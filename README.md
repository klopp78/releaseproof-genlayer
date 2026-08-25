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
- every stored record includes the exact `snapshot_commitments` displayed in the UI
- each accepted release gets an `evidence_bundle_hash`
- the registry stores compact records by `release_id`
- records preserve only essential provenance fields, verdict fields, and accepted-write metadata

## Source Provenance and Readback

ReleaseProof accepts canonical GitHub release/changelog URLs from the same
publisher repository and canonical npm package URLs that match the submitted
package name. The accepted record binds the npm package identity, GitHub
publisher identity, canonical URLs, URL hashes, and rendered snapshot hashes.

### Publisher Ownership Gate

Release verification is deliberately a two-step protocol. Before any release
can be recorded for a GitHub publisher, that publisher must call
`claim_publisher(...)`. The contract renders both the npm package page and a
repository-owned proof file at a versioned path such as:

```text
https://github.com/<owner>/<repo>/blob/<branch>/.releaseproof/ownership.json
```

That file must state the exact npm package, the exact GitHub repository, and
the caller wallet. Validators independently confirm that the npm registry page
associates the package with the same repository and that the proof file binds
the same wallet. The on-chain publisher binding is immutable once claimed.

Only the wallet bound by that proof may call `verify_release` for the
publisher. This prevents an arbitrary caller from front-running a package /
repository / version tuple, while keeping the ownership evidence auditable in
the stored binding hashes and source URLs.

### Binding Enforcement (v3)

The validator path rejects a proposed binding unless both the leader result and
the validator's independently recomputed result are `valid`, repository-matched,
and wallet-matched. Release registration then loads that accepted binding and
requires both its GitHub publisher identity and its stored npm package identity
to exactly equal the submitted release identity. A publisher binding for one
npm package cannot authorize registration for another package.

The frontend does not query a shared `latest` record after submission. It
extracts the `release_id` returned by the accepted transaction receipt, then
reads that exact stored record back from the contract.

## Contract

```text
contracts/release_proof_verifier.py
```

Runtime pin:

```python
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
```

The contract uses the supported GenLayer SDK form:

- `class ReleaseProofVerifier(gl.Contract)`
- `@gl.public.write`
- `@gl.public.view`
- `gl.vm.run_nondet_unsafe(...)`
- `gl.nondet.web.render(...)`
- `gl.nondet.exec_prompt(...)`

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

Publisher claim method:

```python
claim_publisher(
    package_name: str,
    github_repository_url: str,
    npm_registry_url: str,
    ownership_proof_url: str,
) -> str
```

Main view methods:

```python
get_release_count() -> u64
get_latest_release_id() -> str
get_release(release_id: str) -> str
list_release_ids() -> str
get_publisher_binding(publisher_identity: str) -> str
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
npm run contract:check
npm run dev
```

To submit transactions, use a browser wallet connected to GenLayer Studio.

## Reproducible Contract Check

The repository includes a deterministic preflight check for the contract source:

```bash
npm run contract:check
```

The check validates:

- the pinned `py-genlayer` runtime header is present
- `ReleaseProofVerifier` inherits `gl.Contract`
- all public read/write methods are decorated with `gl.public`
- unsupported legacy SDK calls are absent
- GenLayer nondeterministic consensus, web render, and prompt calls are present
- release ID formatting is deterministic
