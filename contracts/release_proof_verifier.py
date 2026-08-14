from genlayer import *


class ReleaseProofVerifier(Contract):
    releases: TreeMap[str, str]
    release_ids: DynArray[str]

    def __init__(self):
        self.releases = TreeMap[str, str]()
        self.release_ids = DynArray[str]()

    @public.write
    def verify_release(
        self,
        package_name: str,
        version: str,
        github_release_url: str,
        registry_url: str,
        changelog_url: str,
    ) -> str:
        assert len(package_name.strip()) >= 3, "package_name_too_short"
        assert len(version.strip()) >= 1, "version_required"

        urls = [github_release_url, registry_url, changelog_url]
        for url in urls:
            assert url.startswith("https://"), "https_sources_required"

        assert self._host(github_release_url) != self._host(registry_url), (
            "github_and_registry_must_be_independent"
        )

        release_id = self._release_id(package_name, version)
        assert self.releases.get(release_id, "") == "", "release_already_verified"

        github_page = gl.get_webpage(github_release_url)
        registry_page = gl.get_webpage(registry_url)
        changelog_page = gl.get_webpage(changelog_url)

        source_manifest = [
            self._source_manifest("github_release", github_release_url, github_page),
            self._source_manifest("package_registry", registry_url, registry_page),
            self._source_manifest("changelog", changelog_url, changelog_page),
        ]
        evidence_bundle_hash = self._hash(
            package_name
            + "|"
            + version
            + "|"
            + source_manifest[0]["snapshot_hash"]
            + "|"
            + source_manifest[1]["snapshot_hash"]
            + "|"
            + source_manifest[2]["snapshot_hash"]
        )

        prompt = f"""
You are a GenLayer validator reviewing software release provenance.

Package: {package_name}
Version: {version}

GitHub release source:
{github_page[:6000]}

Package registry source:
{registry_page[:6000]}

Changelog or docs source:
{changelog_page[:6000]}

Return strict JSON only with:
status: one of verified, mismatch, incomplete, risky
confidence: integer 0-100
version_match: true if the requested version is present in both GitHub release and registry evidence
tag_match: true if the GitHub release or tag clearly maps to the requested version
registry_match: true if the registry evidence clearly shows the requested package and version
changelog_match: true if the changelog/docs reference the requested version or release
risk_flags: short array of strings
summary: one concise sentence explaining the provenance result
"""

        result = gl.exec_prompt(prompt)
        parsed = gl.json_loads(result)

        status = parsed["status"]
        assert status in ["verified", "mismatch", "incomplete", "risky"], "bad_status"

        confidence = u64(parsed["confidence"])
        assert confidence <= 100, "bad_confidence"

        record = {
            "release_id": release_id,
            "package_name": package_name,
            "version": version,
            "submitted_by": str(gl.msg.sender),
            "source_manifest": source_manifest,
            "evidence_bundle_hash": evidence_bundle_hash,
            "accepted_write": {
                "release_id": release_id,
                "registry_sequence": len(self.release_ids) + 1,
                "evidence_bundle_hash": evidence_bundle_hash,
            },
            "result": {
                "status": status,
                "confidence": confidence,
                "version_match": bool(parsed["version_match"]),
                "tag_match": bool(parsed["tag_match"]),
                "registry_match": bool(parsed["registry_match"]),
                "changelog_match": bool(parsed["changelog_match"]),
                "risk_flags": parsed["risk_flags"],
                "evidence_bundle_hash": evidence_bundle_hash,
                "summary": parsed["summary"],
            },
        }

        self.releases[release_id] = gl.json_dumps(record)
        self.release_ids.append(release_id)
        return release_id

    @public.view
    def get_release_count(self) -> u64:
        return len(self.release_ids)

    @public.view
    def get_latest_release_id(self) -> str:
        assert len(self.release_ids) > 0, "no_releases"
        return self.release_ids[len(self.release_ids) - 1]

    @public.view
    def get_release(self, release_id: str) -> str:
        record = self.releases.get(release_id, "")
        assert record != "", "release_not_found"
        return record

    @public.view
    def list_release_ids(self) -> str:
        return gl.json_dumps(self.release_ids)

    def _release_id(self, package_name: str, version: str) -> str:
        normalized = package_name.strip().lower() + "@" + version.strip().lower()
        return "rel_" + self._hash(normalized)[:20]

    def _source_manifest(self, source_type: str, url: str, rendered_page: str) -> dict:
        return {
            "source_type": source_type,
            "host": self._host(url),
            "url_hash": self._hash(url),
            "snapshot_hash": self._hash(rendered_page[:12000]),
        }

    def _host(self, url: str) -> str:
        without_scheme = url.split("://", 1)[1]
        return without_scheme.split("/", 1)[0].lower()

    def _hash(self, value: str) -> str:
        return gl.sha256(value.encode()).hex()
