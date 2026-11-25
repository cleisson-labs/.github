"""Assemble and verify release assets; publish only a complete draft."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def asset_name(name):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]*", name):
        raise ValueError(f"Invalid release filename {name!r}")
    if name == "SHA256SUMS" or name.endswith(".sha256"):
        raise ValueError(f"Checksum filename used as an archive: {name}")
    return name


def regular_file(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Expected a nonempty regular file: {path.name}")
    return path


def file_digest(path):
    with regular_file(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checksums(digests, combined):
    lines = {name: f"{digest}  {name}\n" for name, digest in sorted(digests.items())}
    if combined:
        return {"SHA256SUMS": "".join(lines.values())}
    return {f"{name}.sha256": line for name, line in lines.items()}


def assemble(parts, destination, manifest, combined):
    names = [asset_name(line) for line in manifest.splitlines()]
    if not names or len({name.casefold() for name in names}) != len(names):
        raise ValueError("Release manifest is empty or contains duplicate names")
    archives = {}
    for part in parts.iterdir():
        if part.is_symlink() or not part.is_dir():
            raise ValueError(f"Expected a release part directory: {part.name}")
        for path in part.iterdir():
            if path.name in archives:
                raise ValueError(f"Duplicate release asset: {path.name}")
            archives[path.name] = regular_file(path)
    if set(archives) != set(names):
        raise ValueError(
            f"Release manifest mismatch: {sorted(set(archives) ^ set(names))}"
        )
    destination.mkdir()
    for name, path in archives.items():
        shutil.copyfile(path, destination / name)
    digests = {name: file_digest(destination / name) for name in names}
    for name, contents in checksums(digests, combined).items():
        (destination / name).write_text(contents, encoding="ascii")
    verify(destination)


def verify(directory):
    files = {path.name: regular_file(path) for path in directory.iterdir()}
    archives = {
        asset_name(name): file_digest(path)
        for name, path in files.items()
        if name != "SHA256SUMS" and not name.endswith(".sha256")
    }
    if not archives:
        raise ValueError("Release bundle contains no archives")
    expected = checksums(archives, "SHA256SUMS" in files)
    if set(files) != set(archives) | set(expected):
        raise ValueError(
            "Release bundle checksum inventory does not match its archives"
        )
    for name, contents in expected.items():
        if files[name].read_bytes() != contents.encode("ascii"):
            raise ValueError(f"Incorrect release checksum: {name}")
    return {
        name: "sha256:" + digest
        for name, digest in (
            archives | {name: file_digest(files[name]) for name in expected}
        ).items()
    }


def github(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if args[:2] == ("release", "view"):
        if result.returncode and result.stderr.strip() == "release not found":
            return None
        if not result.returncode:
            return json.loads(result.stdout)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"gh {args[0]} {args[1]} failed")
    return None


def remote_digests(release):
    return {asset["name"]: asset["digest"] for asset in release["assets"]}


def publish(directory, tag, title, notes, generate_notes, gh=github):
    if not re.fullmatch(r"v[0-9][A-Za-z0-9.+-]*", tag):
        raise ValueError("Expected a version tag starting with v and a digit")
    expected = verify(directory)
    query = ("release", "view", tag, "--json", "isDraft,assets")
    release = gh(*query)
    if release is None:
        options = ["--notes", notes] if notes else []
        if generate_notes:
            options.append("--generate-notes")
        gh(
            "release",
            "create",
            tag,
            "--draft",
            "--verify-tag",
            "--title",
            title or tag,
            *options,
        )
        release = gh(*query)
    remote = remote_digests(release)
    if not release["isDraft"]:
        if expected != remote:
            raise ValueError(
                "Existing published release differs; its assets have been preserved"
            )
        return
    if set(remote) - set(expected):
        raise ValueError("Draft contains assets outside the release manifest")
    changed = [
        str(directory / name) for name in expected if expected[name] != remote.get(name)
    ]
    if changed:
        gh("release", "upload", tag, *changed, "--clobber")
    updated = gh(*query)
    if remote_digests(updated) != expected or not updated["isDraft"]:
        raise ValueError("Draft verification failed before publication")
    gh("release", "edit", tag, "--draft=false", "--verify-tag")


if __name__ == "__main__":
    dist = Path("dist")
    (command,) = sys.argv[1:]
    if command == "assemble":
        assemble(
            Path("parts"), dist, os.environ["ASSETS"], os.environ["COMBINED"] == "true"
        )
    elif command == "verify":
        verify(dist)
    elif command == "publish":
        publish(
            dist,
            os.environ["GITHUB_REF_NAME"],
            os.environ["TITLE"],
            os.environ["NOTES"],
            os.environ["GENERATE_NOTES"] == "true",
        )
    else:
        raise SystemExit("Expected assemble, verify or publish")
