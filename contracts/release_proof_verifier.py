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
    summary: str


class ReleaseProofVerifier(gl.Contract):
    """Persistent registry of consensus-reviewed software release provenance."""

    release_count: u64
    latest_release_id: str
    release_ids: DynArray[str]
    releases: TreeMap[str, str]

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

        source_urls = _validate_sources([github_release_url, registry_url, changelog_url])
        source_manifest = _source_manifest(source_urls)
        if source_manifest[0]["host"] == source_manifest[1]["host"]:
            raise Exception("github_and_registry_must_be_independent")

        release_id = _release_id(package_name, version)
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

            return True

        agreed_json = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        verdict = json.loads(agreed_json)

        self.release_count = u64(int(self.release_count) + 1)
        record = {
            "release_id": release_id,
            "package_name": package_name,
            "version": version,
            "source_urls": source_urls,
            "source_manifest": source_manifest,
            "submitted_by": str(gl.message.sender_address),
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

    evidence_bundle_hash = _sha256(json.dumps(evidence_hashes, separators=(",", ":")))

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

    return ReleaseVerdict(
        status=status,
        confidence=u8(confidence),
        version_match=bool(data["version_match"]),
        tag_match=bool(data["tag_match"]),
        registry_match=bool(data["registry_match"]),
        changelog_match=bool(data["changelog_match"]),
        risk_flags_json=risk_flags_json,
        evidence_bundle_hash=evidence_bundle_hash,
        summary=summary,
    )


def _validate_sources(source_urls: typing.Sequence[str]) -> typing.Sequence[str]:
    normalized = []
    seen = set()
    for raw_url in source_urls:
        url = str(raw_url).strip()
        if not url.startswith("https://"):
            raise Exception("sources_must_use_https")
        if len(url) > 500:
            raise Exception("source_url_too_long")
        key = url.rstrip("/").lower()
        if key in seen:
            raise Exception("duplicate_source")
        seen.add(key)
        normalized.append(url)
    return normalized


def _source_manifest(source_urls: typing.Sequence[str]) -> typing.Sequence[dict]:
    source_types = ["github_release", "package_registry", "changelog"]
    manifest = []
    for index, url in enumerate(source_urls):
        manifest.append(
            {
                "source_index": index + 1,
                "source_type": source_types[index],
                "host": _url_host(url),
                "url_hash": _sha256(url),
            }
        )
    return manifest


def _release_id(package_name: str, version: str) -> str:
    normalized = package_name.strip().lower() + "@" + version.strip().lower()
    return "rel_" + _sha256(normalized)[:20]


def _url_host(url: str) -> str:
    without_scheme = url.split("://", 1)[1]
    return without_scheme.split("/", 1)[0].lower()


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
