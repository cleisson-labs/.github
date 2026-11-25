import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.release import assemble, publish, verify


class ReleaseTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parts = Path(temporary.name, "parts")
        self.dist = Path(temporary.name, "dist")
        self.part = self.parts / "release-part-linux"
        self.part.mkdir(parents=True)
        self.archive = self.part / "app-linux.zip"
        self.archive.write_bytes(b"standalone binary")
        self.expected = "app-linux.zip"
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def test_public_checksum_formats(self):
        for combined in (True, False):
            destination = self.dist / str(combined)
            destination.parent.mkdir(exist_ok=True)
            assemble(self.parts, destination, self.expected, combined)
            checksum = "SHA256SUMS" if combined else "app-linux.zip.sha256"
            self.assertEqual(
                (destination / checksum).read_text(), f"{self.digest}  app-linux.zip\n"
            )
            self.assertEqual(set(verify(destination)), {checksum, self.archive.name})

    def test_missing_unexpected_or_duplicate_platform_blocks_assembly(self):
        with self.assertRaises(ValueError):
            assemble(self.parts, self.dist, self.expected + "\napp-mac.zip", False)
        with self.assertRaises(ValueError):
            assemble(self.parts, self.dist, "unrelated.zip", False)
        second = self.parts / "release-part-macos"
        second.mkdir()
        (second / self.archive.name).write_bytes(b"wrong platform")
        with self.assertRaises(ValueError):
            assemble(self.parts, self.dist, self.expected, False)

    def test_rejects_traversal_symlinks_empty_files_and_duplicate_manifest_entries(
        self,
    ):
        for name in ("../escape", "SHA256SUMS", self.expected + "\n" + self.expected):
            with self.subTest(name=name), self.assertRaises(ValueError):
                assemble(self.parts, self.dist, name, False)
        self.archive.write_bytes(b"")
        with self.assertRaises(ValueError):
            assemble(self.parts, self.dist, self.expected, False)
        self.archive.unlink()
        self.archive.symlink_to(Path(__file__).resolve())
        with self.assertRaises(ValueError):
            assemble(self.parts, self.dist, self.expected, False)

    def test_corruption_or_missing_checksum_blocks_attestation(self):
        assemble(self.parts, self.dist, self.expected, False)
        (self.dist / "app-linux.zip").write_bytes(b"tampered archive")
        with self.assertRaises(ValueError):
            verify(self.dist)
        (self.dist / "app-linux.zip.sha256").unlink()
        with self.assertRaises(ValueError):
            verify(self.dist)

    def test_published_release_is_idempotent_only_for_identical_digests(self):
        assemble(self.parts, self.dist, self.expected, True)
        assets = [
            {"name": name, "digest": digest}
            for name, digest in verify(self.dist).items()
        ]
        gh = Mock(return_value={"isDraft": False, "assets": assets})
        publish(self.dist, "v1.0.0", "App", "", True, gh)
        self.assertEqual(gh.call_count, 1)
        assets[0]["digest"] = "sha256:changed"
        with self.assertRaises(ValueError):
            publish(self.dist, "v1.0.0", "App", "", True, gh)
        self.assertEqual(gh.call_count, 2)

    def test_draft_retry_verifies_remote_digests_before_publication(self):
        assemble(self.parts, self.dist, self.expected, False)
        assets = [
            {"name": name, "digest": digest}
            for name, digest in verify(self.dist).items()
        ]
        draft = {"isDraft": True, "assets": assets[:1]}
        gh = Mock(side_effect=[draft, None, {"isDraft": True, "assets": assets}, None])
        publish(self.dist, "v1.0.0", "", "Changes", True, gh)
        self.assertEqual(
            gh.call_args_list[1].args[0:3], ("release", "upload", "v1.0.0")
        )
        self.assertEqual(
            gh.call_args_list[-1].args,
            ("release", "edit", "v1.0.0", "--draft=false", "--verify-tag"),
        )
        bad = Mock(side_effect=[draft, None, draft])
        with self.assertRaises(ValueError):
            publish(self.dist, "v1.0.0", "", "Changes", True, bad)
        self.assertEqual(bad.call_count, 3)

    def test_create_keeps_changelog_and_generated_notes_in_an_unpublished_draft(self):
        assemble(self.parts, self.dist, self.expected, False)
        remote = [
            {"name": name, "digest": digest}
            for name, digest in verify(self.dist).items()
        ]
        gh = Mock(
            side_effect=[
                None,
                None,
                {"isDraft": True, "assets": []},
                None,
                {"isDraft": True, "assets": remote},
                None,
            ]
        )
        publish(self.dist, "v1.0.0", "", "Reviewed\nchanges", True, gh)
        self.assertEqual(
            gh.call_args_list[1].args,
            (
                "release",
                "create",
                "v1.0.0",
                "--draft",
                "--verify-tag",
                "--title",
                "v1.0.0",
                "--notes",
                "Reviewed\nchanges",
                "--generate-notes",
            ),
        )
        self.assertEqual(gh.call_args_list[-1].args[0:2], ("release", "edit"))

    def test_unexpected_existing_assets_are_never_deleted_or_published(self):
        assemble(self.parts, self.dist, self.expected, False)
        gh = Mock(
            return_value={
                "isDraft": True,
                "assets": [{"name": "unexpected", "digest": None}],
            }
        )
        with self.assertRaises(ValueError):
            publish(self.dist, "v1.0.0", "", "", True, gh)
        self.assertEqual(gh.call_count, 1)

    def test_native_binary_checksum_sidecar_is_verified_and_preserved(self):
        body = f"{self.digest} *{self.archive.name}\n".encode("ascii")
        supplied = self.part / f"{self.archive.name}.sha256"
        supplied.write_bytes(body)
        assemble(self.parts, self.dist, self.expected, False)
        self.assertEqual((self.dist / supplied.name).read_bytes(), body)
        verify(self.dist)
        for contents in (
            body.replace(b"*", b"*../"),
            b"0" * 64 + body[64:],
            body + body,
        ):
            supplied.write_bytes(contents)
            with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
                assemble(self.parts, Path(tmp, "dist"), self.expected, False)

    def test_download_action_flattens_a_single_matching_artifact(self):
        assemble(self.part, self.dist, self.expected, False)
        self.assertEqual(verify(self.dist)[self.archive.name], "sha256:" + self.digest)
