# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import hashlib
import json
import typing


class ReleaseVerdict(typing.NamedTuple):
    status: str
    confidence: u8
    version_match: bool
    tag_match: bool
    registry_match: bool
    changelog_match: bool
    risk_flags_json: str
    evidence_bundle_hash: str
    snapshot_commitments_json: str
    summary: str


class ReleaseProofVerifier(gl.Contract):
    """Persistent registry of consensus-reviewed software release provenance."""

    release_count: u64
    latest_release_id: str
    release_ids: DynArray[str]
    releases: TreeMap[str, str]
    publisher_owners: TreeMap[str, str]
    publisher_bindings: TreeMap[str, str]

    def __init__(self):
        self.release_count = u64(0)
        self.latest_release_id = ""

    @gl.public.view
    def get_release_count(self) -> u64:
        return self.release_count

    @gl.public.view
    def get_latest_release_id(self) -> str:
        return self.latest_release_id

    @gl.public.view
    def get_release(self, release_id: str) -> str:
        return self.releases.get(release_id, "")

    @gl.public.view
    def list_release_ids(self) -> str:
        return json.dumps([release_id for release_id in self.release_ids], separators=(",", ":"))

    @gl.public.view
    def get_publisher_binding(self, publisher_identity: str) -> str:
        return self.publisher_bindings.get(publisher_identity, "")

    @gl.public.write
    def claim_publisher(
        self,
        package_name: str,
        github_repository_url: str,
        npm_registry_url: str,
        ownership_proof_url: str,
    ) -> str:
        """Bind a package to the GitHub publisher that controls its proof file."""
        normalized_package = _normalize_package_name(package_name)
        publisher = _canonical_github_repository(github_repository_url)
        registry = _canonical_npm_source(npm_registry_url, normalized_package)
        proof = _canonical_ownership_proof(ownership_proof_url, publisher)
        claimant = str(gl.message.sender_address).lower()

        if len(self.publisher_owners.get(publisher["publisher_identity"], "")) > 0:
            raise Exception("publisher_already_claimed")

        def leader_fn():
            return _adjudicate_publisher_binding(
                normalized_package, publisher, registry, proof, claimant
            )

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                proposed = json.loads(leader_result.calldata)
                independent = json.loads(
                    _adjudicate_publisher_binding(
                        normalized_package, publisher, registry, proof, claimant
                    )
                )
            except Exception:
                return False
            return (
                proposed.get("valid") is True
                and proposed.get("binding_hash") == independent.get("binding_hash")
                and proposed.get("repository_match") == independent.get("repository_match")
                and proposed.get("wallet_match") == independent.get("wallet_match")
            )

        binding = json.loads(gl.vm.run_nondet_unsafe(leader_fn, validator_fn))
        if binding.get("valid") is not True:
            raise Exception("publisher_binding_not_proven")

        binding["claimed_by"] = claimant
        binding["package_identity"] = registry["package_identity"]
        self.publisher_owners[publisher["publisher_identity"]] = claimant
        self.publisher_bindings[publisher["publisher_identity"]] = json.dumps(
            binding, sort_keys=True, separators=(",", ":")
        )
        return publisher["publisher_identity"]

    @gl.public.write
    def verify_release(
        self,
        package_name: str,
        version: str,
        github_release_url: str,
        registry_url: str,
        changelog_url: str,
    ) -> str:
        if len(package_name.strip()) < 3:
            raise Exception("package_name_too_short")
        if len(version.strip()) == 0:
            raise Exception("version_required")

        normalized_package = _normalize_package_name(package_name)
        source_manifest = _canonical_sources(
            normalized_package,
            github_release_url,
            registry_url,
            changelog_url,
        )
        source_urls = [source["canonical_url"] for source in source_manifest]
        publisher_identity = source_manifest[0]["publisher_identity"]
        owner = self.publisher_owners.get(publisher_identity, "")
        if len(owner) == 0:
            raise Exception("publisher_must_be_claimed_before_release_verification")
        if owner.lower() != str(gl.message.sender_address).lower():
            raise Exception("only_bound_publisher_wallet_can_verify_release")

        release_id = _release_id(
            source_manifest[1]["package_identity"],
            source_manifest[0]["publisher_identity"],
            version,
        )
        if len(self.releases.get(release_id, "")) > 0:
            raise Exception("release_already_verified")

        def leader_fn():
            return _adjudicate_release(package_name, version, source_urls, source_manifest)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False

            try:
                proposed = _parse_verdict(leader_result.calldata)
                independent = _parse_verdict(
                    _adjudicate_release(package_name, version, source_urls, source_manifest)
                )
            except Exception:
                return False

            if proposed.status != independent.status:
                return False
            if proposed.evidence_bundle_hash != independent.evidence_bundle_hash:
                return False
            if abs(int(proposed.confidence) - int(independent.confidence)) > 20:
                return False
            if proposed.version_match != independent.version_match:
                return False
            if proposed.registry_match != independent.registry_match:
                return False
            if proposed.risk_flags_json != independent.risk_flags_json:
                return False
            if proposed.snapshot_commitments_json != independent.snapshot_commitments_json:
                return False

            return True

        agreed_json = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        verdict = json.loads(agreed_json)

        self.release_count = u64(int(self.release_count) + 1)
        record = {
            "schema_version": "releaseproof.v2",
            "release_id": release_id,
            "package_name": normalized_package,
            "version": version,
            "package_identity": source_manifest[1]["package_identity"],
            "publisher_identity": source_manifest[0]["publisher_identity"],
            "source_urls": source_urls,
            "source_manifest": source_manifest,
            "snapshot_commitments": verdict["snapshot_commitments"],
            "evidence_bundle_hash": verdict["evidence_bundle_hash"],
            "submitted_by": str(gl.message.sender_address),
            "publisher_binding": self.publisher_bindings.get(publisher_identity, ""),
            "result": verdict,
            "accepted_write": {
                "release_id": release_id,
                "registry_sequence": int(self.release_count),
                "evidence_bundle_hash": verdict["evidence_bundle_hash"],
            },
        }

        self.releases[release_id] = json.dumps(record, sort_keys=True, separators=(",", ":"))
        self.release_ids.append(release_id)
        self.latest_release_id = release_id
        return release_id


def _adjudicate_publisher_binding(
    package_name: str,
    publisher: dict,
    registry: dict,
    proof: dict,
    claimant: str,
) -> str:
    registry_text = gl.nondet.web.render(registry["canonical_url"], mode="text")[:6000]
    proof_text = gl.nondet.web.render(proof["canonical_url"], mode="text")[:3000]
    binding_hash = _sha256(
        publisher["publisher_identity"]
        + "|"
        + registry["package_identity"]
        + "|"
        + proof["canonical_url"]
        + "|"
        + claimant
        + "|"
        + _sha256(registry_text)
        + "|"
        + _sha256(proof_text)
    )
    prompt = f"""
You verify a package publisher ownership binding for a GenLayer contract.

Package: {package_name}
Expected GitHub repository: {publisher["canonical_url"]}
Expected caller wallet: {claimant}
Registry page text: {registry_text}
Repository-owned proof-file text: {proof_text}

The proof file must explicitly state the exact npm package '{package_name}', the exact
GitHub repository '{publisher["canonical_url"]}', and the exact wallet '{claimant}'.
The registry page must visibly associate the package with that same GitHub repository.
Return only minified JSON with keys valid, repository_match, wallet_match, summary,
binding_hash. binding_hash must be exactly '{binding_hash}'.
"""
    data = json.loads(gl.nondet.exec_prompt(prompt))
    return json.dumps(
        {
            "valid": bool(data.get("valid")),
            "repository_match": bool(data.get("repository_match")),
            "wallet_match": bool(data.get("wallet_match")),
            "summary": str(data.get("summary", ""))[:350],
            "binding_hash": str(data.get("binding_hash", "")),
            "proof_url": proof["canonical_url"],
            "registry_snapshot_hash": _sha256(registry_text),
            "proof_snapshot_hash": _sha256(proof_text),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _adjudicate_release(
    package_name: str,
    version: str,
    source_urls: typing.Sequence[str],
    source_manifest: typing.Sequence[dict],
) -> str:
    source_payloads = []
    evidence_hashes = []
    for index, url in enumerate(source_urls):
        page = gl.nondet.web.render(url, mode="text")
        rendered_text = page[:6000]
        snapshot_hash = _sha256(rendered_text)
        evidence_hashes.append(snapshot_hash)
        source_payloads.append(
            {
                "source_index": index + 1,
                "source_type": source_manifest[index]["source_type"],
                "host": source_manifest[index]["host"],
                "url_hash": source_manifest[index]["url_hash"],
                "snapshot_hash": snapshot_hash,
                "snapshot_chars": len(rendered_text),
                "text": rendered_text,
            }
        )

    snapshot_commitments = []
    for source, snapshot_hash, rendered in zip(source_manifest, evidence_hashes, source_payloads):
        snapshot_commitments.append(
            {
                "source_index": source["source_index"],
                "source_type": source["source_type"],
                "canonical_url": source["canonical_url"],
                "package_identity": source["package_identity"],
                "publisher_identity": source["publisher_identity"],
                "url_hash": source["url_hash"],
                "snapshot_hash": snapshot_hash,
                "snapshot_chars": rendered["snapshot_chars"],
            }
        )
    evidence_bundle_hash = _sha256(
        json.dumps(snapshot_commitments, sort_keys=True, separators=(",", ":"))
    )

    prompt = f"""
You are reviewing software release provenance for GenLayer consensus.

Requested package:
{package_name}

Requested version:
{version}

Source provenance manifest:
{json.dumps(source_manifest)}

Rendered evidence snapshots:
{json.dumps(source_payloads)}

Return only minified JSON with exactly these keys:
- status: one of "verified", "mismatch", "incomplete", "risky"
- confidence: integer from 0 to 100
- version_match: true when the requested version appears in release and registry evidence
- tag_match: true when GitHub release or tag evidence maps to the requested version
- registry_match: true when the registry evidence clearly names the requested package and version
- changelog_match: true when changelog or docs evidence references the requested release
- risk_flags: short array of stable lowercase strings
- evidence_bundle_hash: exactly "{evidence_bundle_hash}"
- summary: concise explanation under 450 characters

Rules:
- Do not mark verified unless independent GitHub and registry evidence both support the package/version.
- Use incomplete when a source is inaccessible, thin, or does not directly mention the requested release.
- Use mismatch when sources disagree on package identity, version, date, tag, or release contents.
- Use risky when there are strong warning signs but not enough evidence for mismatch.
- Do not invent support that is not visible in the rendered source text.
"""

    raw = gl.nondet.exec_prompt(prompt)
    data = json.loads(raw)
    normalized = {
        "status": str(data["status"]).lower(),
        "confidence": max(0, min(100, int(data["confidence"]))),
        "version_match": bool(data["version_match"]),
        "tag_match": bool(data["tag_match"]),
        "registry_match": bool(data["registry_match"]),
        "changelog_match": bool(data["changelog_match"]),
        "risk_flags": [str(flag).lower()[:80] for flag in data["risk_flags"][:8]],
        "evidence_bundle_hash": str(data["evidence_bundle_hash"]),
        "snapshot_commitments": snapshot_commitments,
        "summary": str(data["summary"])[:450],
    }
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))


def _parse_verdict(raw_json: str) -> ReleaseVerdict:
    data = json.loads(raw_json)
    status = str(data["status"]).lower()
    confidence = int(data["confidence"])
    risk_flags = data["risk_flags"]
    risk_flags_json = json.dumps(risk_flags, sort_keys=True, separators=(",", ":"))
    evidence_bundle_hash = str(data["evidence_bundle_hash"])
    snapshot_commitments_json = json.dumps(
        data["snapshot_commitments"], sort_keys=True, separators=(",", ":")
    )
    summary = str(data["summary"])

    if status not in ("verified", "mismatch", "incomplete", "risky"):
        raise Exception("invalid status")
    if confidence < 0 or confidence > 100:
        raise Exception("invalid confidence")
    if len(evidence_bundle_hash) != 64:
        raise Exception("invalid evidence hash")
    if len(summary) == 0 or len(summary) > 450:
        raise Exception("invalid summary")
    if len(risk_flags) > 8:
        raise Exception("too many risk flags")
    if len(data["snapshot_commitments"]) != 3:
        raise Exception("invalid snapshot commitments")

    return ReleaseVerdict(
        status=status,
        confidence=u8(confidence),
        version_match=bool(data["version_match"]),
        tag_match=bool(data["tag_match"]),
        registry_match=bool(data["registry_match"]),
        changelog_match=bool(data["changelog_match"]),
        risk_flags_json=risk_flags_json,
        evidence_bundle_hash=evidence_bundle_hash,
        snapshot_commitments_json=snapshot_commitments_json,
        summary=summary,
    )


def _canonical_sources(
    package_name: str,
    github_release_url: str,
    registry_url: str,
    changelog_url: str,
) -> typing.Sequence[dict]:
    github = _canonical_github_source(github_release_url, "github_release")
    registry = _canonical_npm_source(registry_url, package_name)
    changelog = _canonical_github_source(changelog_url, "changelog")

    if changelog["publisher_identity"] != github["publisher_identity"]:
        raise Exception("changelog_must_belong_to_release_publisher")

    return [
        _manifest_entry(1, github, registry["package_identity"]),
        _manifest_entry(2, registry, registry["package_identity"]),
        _manifest_entry(3, changelog, registry["package_identity"]),
    ]


def _manifest_entry(index: int, source: dict, package_identity: str) -> dict:
    return {
        "source_index": index,
        "source_type": source["source_type"],
        "host": source["host"],
        "canonical_url": source["canonical_url"],
        "package_identity": package_identity,
        "publisher_identity": source["publisher_identity"],
        "url_hash": _sha256(source["canonical_url"]),
    }


def _canonical_github_source(raw_url: str, source_type: str) -> dict:
    host, parts = _url_parts(raw_url)
    if host != "github.com" or len(parts) < 3:
        raise Exception("github_source_must_be_canonical")
    owner = parts[0].lower()
    repository = parts[1].lower()
    if parts[2] not in ("releases", "tags", "blob"):
        raise Exception("github_source_must_be_release_tag_or_changelog")
    canonical_url = "https://github.com/" + "/".join(parts)
    return {
        "source_type": source_type,
        "host": host,
        "canonical_url": canonical_url,
        "publisher_identity": "github:" + owner + "/" + repository,
    }


def _canonical_github_repository(raw_url: str) -> dict:
    host, parts = _url_parts(raw_url)
    if host != "github.com" or len(parts) != 2:
        raise Exception("github_repository_must_be_canonical")
    owner = parts[0].lower()
    repository = parts[1].lower()
    return {
        "canonical_url": "https://github.com/" + owner + "/" + repository,
        "publisher_identity": "github:" + owner + "/" + repository,
    }


def _canonical_ownership_proof(raw_url: str, publisher: dict) -> dict:
    host, parts = _url_parts(raw_url)
    expected_prefix = publisher["canonical_url"].replace("https://github.com/", "").split("/")
    if (
        host != "github.com"
        or len(parts) < 5
        or parts[0].lower() != expected_prefix[0]
        or parts[1].lower() != expected_prefix[1]
        or parts[2] != "blob"
        or ".releaseproof" not in parts
    ):
        raise Exception("ownership_proof_must_be_versioned_file_in_publisher_repository")
    return {"canonical_url": "https://github.com/" + "/".join(parts)}


def _canonical_npm_source(raw_url: str, package_name: str) -> dict:
    host, parts = _url_parts(raw_url)
    if host not in ("npmjs.com", "www.npmjs.com") or len(parts) < 2 or parts[0] != "package":
        raise Exception("registry_must_be_canonical_npm_package_url")

    package_end = 3 if parts[1].startswith("@") else 2
    if len(parts) < package_end:
        raise Exception("registry_package_missing")
    registry_package = "/".join(parts[1:package_end])
    if _normalize_package_name(registry_package) != package_name:
        raise Exception("registry_package_identity_mismatch")

    canonical_url = "https://www.npmjs.com/" + "/".join(parts)
    return {
        "source_type": "package_registry",
        "host": "www.npmjs.com",
        "canonical_url": canonical_url,
        "publisher_identity": "npm:" + package_name,
        "package_identity": "npm:" + package_name,
    }


def _normalize_package_name(raw_name: str) -> str:
    package_name = str(raw_name).strip().lower()
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-._@/"
    if len(package_name) < 3 or any(char not in allowed for char in package_name):
        raise Exception("invalid_package_name")
    if package_name.count("/") > 1 or ("/" in package_name and not package_name.startswith("@")):
        raise Exception("invalid_package_name")
    return package_name


def _release_id(package_identity: str, publisher_identity: str, version: str) -> str:
    normalized = package_identity + "|" + publisher_identity + "|" + version.strip().lower()
    return "rel_" + _sha256(normalized)[:20]


def _url_parts(raw_url: str) -> typing.Tuple[str, typing.Sequence[str]]:
    url = str(raw_url).strip()
    if not url.startswith("https://") or len(url) > 500:
        raise Exception("sources_must_use_canonical_https")
    if "?" in url or "#" in url:
        raise Exception("sources_must_not_include_query_or_fragment")
    without_scheme = url[8:]
    if "/" not in without_scheme:
        raise Exception("source_path_required")
    host, path = without_scheme.split("/", 1)
    parts = [part for part in path.split("/") if len(part) > 0]
    if len(parts) == 0:
        raise Exception("source_path_required")
    return host.lower(), parts


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
