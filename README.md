# ReleaseProof for GenLayer

ReleaseProof is a GenLayer Project for checking whether an open-source software release is consistent across the sources developers and AI agents actually rely on: GitHub releases or tags, package registries, and changelogs.

The project is designed for a real trust problem in the agentic software stack. Before an agent installs, calls, or routes through a dependency, it should be able to ask whether the claimed package version is backed by independent release evidence.

## Live Demo

- App: https://klopp78.github.io/releaseproof-genlayer/
- GitHub repo: https://github.com/klopp78/releaseproof-genlayer
- Contract source: `contracts/release_proof_verifier.py`

Studio deployment can be added by replacing `RELEASE_PROOF_CONTRACT_ADDRESS` in `lib/genlayer.ts` with the deployed contract address.

## What It Verifies

The user submits:

- package name
- version
- GitHub release or tag URL
- package registry URL, such as npm or PyPI
- changelog or documentation URL

GenLayer validators independently read those sources and produce a compact provenance record:

- `status`: `verified`, `mismatch`, `incomplete`, or `risky`
- `confidence`
- `version_match`
- `tag_match`
- `registry_match`
- `changelog_match`
- `risk_flags`
- `summary`

## Why This Fits GenLayer

Release provenance is not a normal deterministic check. The useful judgement comes from reading live web evidence, interpreting release pages, and comparing multiple public sources that may be incomplete, inconsistent, renamed, delayed, or stale.

GenLayer is used for:

- nondeterministic web reads from GitHub, registries, and docs
- consensus over judgement-heavy release evidence
- a durable registry of accepted release checks
- evidence hashes that keep storage compact while preserving auditability

## Storage-Conscious Design

This project follows the Studio storage guidance announced by the GenLayer team:

- large rendered pages are not stored on-chain
- each source gets a `snapshot_hash`
- each URL gets a `url_hash`
- each accepted release gets an `evidence_bundle_hash`
- the registry stores compact records by `release_id`
- records preserve only essential provenance fields, verdict fields, and accepted-write metadata

## Contract

```text
contracts/release_proof_verifier.py
```

Main write method:

```python
verify_release(
    package_name: str,
    version: str,
    github_release_url: str,
    registry_url: str,
    changelog_url: str,
) -> str
```

Main view methods:

```python
get_release_count() -> u64
get_latest_release_id() -> str
get_release(release_id: str) -> str
list_release_ids() -> str
```

## Example

```text
Package: genlayer-js
Version: 1.1.8
GitHub: https://github.com/yeagerai/genlayer-js/releases
Registry: https://www.npmjs.com/package/genlayer-js/v/1.1.8
Changelog: https://github.com/yeagerai/genlayer-js/blob/main/CHANGELOG.md
```

Expected output shape:

```json
{
  "release_id": "rel_...",
  "evidence_bundle_hash": "...",
  "result": {
    "status": "verified",
    "confidence": 86,
    "version_match": true,
    "tag_match": true,
    "registry_match": true,
    "changelog_match": true,
    "risk_flags": [],
    "summary": "The release, registry version, and changelog all point to the requested package version."
  }
}
```

## Run Locally

```bash
npm install
npm run dev
```

To submit transactions, use a browser wallet connected to GenLayer Studio.
