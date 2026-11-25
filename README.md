# Cleisson Labs CI/CD

[![CI](https://github.com/cleisson-labs/.github/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/cleisson-labs/.github/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/cleisson-labs/.github)](LICENSE)

This repository supplies GitHub Actions workflows and community defaults for the public Cleisson Labs repositories. Projects own their build commands, compatibility promises, coverage thresholds, asset names and release triggers. The organization profile lives in [profile/README.md](profile/README.md).

## Workflow contracts

Call these files from `.github/workflows/` by their full commit SHA. Inputs and defaults are declared next to `workflow_call` in each file.

| Workflow | What the caller gets |
| --- | --- |
| [security.yml](.github/workflows/security.yml) | actionlint, zizmor, full-history Gitleaks, ShellCheck, incremental shfmt and dependency review on PRs |
| [docs.yml](.github/workflows/docs.yml) | Markdown syntax and offline links. Set `external: true` on a scheduled or manually dispatched default-branch run to check public URLs. |
| [rust.yml](.github/workflows/rust.yml) | rustfmt, Clippy, locked tests and build, optional MSRV, native coverage and a smoke-test binary. The compilation cache is saved by trusted default-branch pushes. |
| [rust-audit.yml](.github/workflows/rust-audit.yml) | cargo-deny advisories on the locked graph, or the full policy when a project supplies `deny.toml`. |
| [c.yml](.github/workflows/c.yml) | Cppcheck via `make analyze`, clang-format for configured projects, optional Clang sanitizers and GCC/gcovr coverage targets. |
| [node.yml](.github/workflows/node.yml) | Node 24 and the project's `npm run validate`, or syntax checking and native test coverage for a manifest-free project. |
| [python.yml](.github/workflows/python.yml) | Python 3.13, checksum-verified Ruff and unittest discovery. |
| [codeql.yml](.github/workflows/codeql.yml) | One language per call. Extraction and any project build use a read-only token. A fresh job submits SARIF. |
| [release-assets.yml](.github/workflows/release-assets.yml) | Assemble an exact list of archive names and SHA-256 checksum files from the current run; return the bundle's artifact ID. |
| [release.yml](.github/workflows/release.yml) | Attest a verified bundle on a version tag, verify provenance, stage a complete draft and publish it. |

Ordinary jobs need `contents: read`. The CodeQL caller also grants `security-events: write`; the called workflow limits that permission to its upload job. The release caller grants `contents: write`, `attestations: write` and `id-token: write` only to the tag-gated release call. Job permissions can only decrease across a workflow call. Keep repository-controlled scripts, PR builds and tests out of jobs with write access.

## Integrate a repository

1. Enable Actions, the dependency graph, Dependabot alerts and security updates, private vulnerability reporting, secret scanning and push protection in the public repository. Use the standard GitHub-hosted runners. Configure CodeQL through the reusable workflow so GitHub has one analysis source per language.
2. Choose a Cleisson Labs CI starter under **Actions → New workflow**. Add the language checks you need and any repository-specific jobs. To find the immutable revision for a version, run `gh api repos/cleisson-labs/.github/commits/v1.0.0 --jq .sha`. Use the full returned SHA after `@` and record the version in a comment on each external `uses` line.
3. Trigger CI on pull requests and default-branch pushes. Add weekly CodeQL, dependency audits and external documentation link checks. For public Scorecard reporting, copy [scorecard.yml](.github/workflows/scorecard.yml) into the consuming repository as a standalone workflow and stagger its schedule. Copy [.github/dependabot.yml](.github/dependabot.yml) locally, then add grouped package ecosystems and their manifest directories. Apply a seven-day cooldown to routine version updates.
4. Include each mandatory job in the local `ci-ok` job's `needs`. Use `if: always()` and require every expected result to equal `success`. A repository using path detection must explicitly validate which jobs may skip for those paths. Run CI for documentation-only PRs so branch protection always receives a conclusion.
5. Verify a PR and its resulting default-branch run, including platform-specific checks. Require the GitHub Actions `ci-ok` context, a pull request, resolved review threads and up-to-date checks. Permit squash merging with zero required independent approvals. Block force pushes and branch deletion.
6. Use CI, license, release, coverage and public Scorecard badges in that order when the project has the corresponding results. Link coverage to the actual report or run. Use a version tag only for a real release.

GitHub falls back to these contribution, conduct, support, security, issue and PR templates when a repository has no local equivalent. A local issue template directory takes precedence as a set. Licenses, workflow files and dependency configurations belong to each repository. Language policy can remain local. The documentation and security workflows explicitly check out their own immutable revision to read their shared configurations and tool digests. [GitHub community file inheritance](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file) · [Reusable workflow identity](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#example-usage-of-job-context-workflow-identity)

## Release contract

Build and smoke-test archives in unprivileged platform jobs. Upload one uniquely named `release-part-*` artifact per producer. Pass the complete expected filenames to the assembly workflow. It rejects missing, unexpected, duplicate, empty or symlinked assets and computes SHA-256 sidecars or a combined `SHA256SUMS` according to the project's public contract.

Pass the resulting `artifact-id` to the tag-gated publication workflow. Only the attestation job can request an OIDC identity. The publisher checks the tag commit, signer workflow, source ref and digest and hosted runner identity. It compares the remote asset inventory and hashes before publishing a draft. A retry resumes a matching draft. If an existing public release differs, publication stops and preserves the existing assets. Use one non-cancelling release concurrency group per tag in the caller. Consumers can verify a downloaded archive with:

```sh
gh attestation verify "$archive" --repo "cleisson-labs/$project" \
  --signer-workflow cleisson-labs/.github/.github/workflows/release.yml \
  --source-ref "refs/tags/$version" --deny-self-hosted-runners
```

GitHub artifact attestations and CodeQL analysis are available for these public repositories. The workflows use standard hosted runners, GitHub artifacts and public upstream releases. [GitHub attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations) · [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

## Maintain and version the infrastructure

Use a PR to update verified pins and tool digests, exercise the language fixtures and rehearse release assembly. After the default branch passes, create an immutable semantic version tag at that tested commit. Patch versions fix compatible behavior, minor versions add optional capabilities, and major versions change caller contracts. Never move a published version tag. Roll back a caller by reverting its pin to a previously verified commit.

The [Linux tool manifest](tools/linux-tools.tsv) names each upstream asset and its SHA-256. Compare its digest with the upstream release metadata before changing it. The installer verifies the exact bytes before extraction. The maintained MIT-licensed actionlint fork recognizes GitHub's workflow identity and self-repository syntax. Gitleaks uses the open-source CLI; the separate Gitleaks GitHub Action requires an organization license. [actionlint](https://github.com/kjanat/actionlint) · [Gitleaks CLI](https://github.com/gitleaks/gitleaks) · [Gitleaks Action licensing](https://github.com/gitleaks/gitleaks-action)

Cargo-deny covers RustSec advisories and supports project license and source policies. Use cargo-llvm-cov where there is a real report, GCC/Clang and gcovr where the builds exercise C, and Ruff with existing unittest suites. Projects can adopt uv when they need Python dependency resolution. Clang sanitizers and native leak tests cover the current C targets. Additional analyzers, alternative test runners, mutation testing and fuzzing need a concrete gap to justify their maintenance cost.
