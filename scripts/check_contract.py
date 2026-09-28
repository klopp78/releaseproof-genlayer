import importlib.util
import json
import pathlib
import sys
import types


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "release_proof_verifier.py"
EXPECTED_DEPENDS = "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6"


class _Public:
    @staticmethod
    def view(fn):
        fn.__genlayer_visibility__ = "view"
        return fn

    @staticmethod
    def write(fn):
        fn.__genlayer_visibility__ = "write"
        return fn


class _Return:
    def __init__(self, calldata="{}"):
        self.calldata = calldata


class _NondetWeb:
    calls = []

    @staticmethod
    def render(url, mode="text"):
        _NondetWeb.calls.append({"url": url, "mode": mode})
        if url == "https://registry.npmjs.org/genlayer-js":
            return json.dumps(
                {
                    "name": "genlayer-js",
                    "repository": {
                        "type": "git",
                        "url": "git+https://github.com/yeagerai/genlayer-js.git",
                    },
                    "versions": {"1.1.8": {"name": "genlayer-js", "version": "1.1.8"}},
                },
                sort_keys=True,
            )
        if url == "https://registry.npmjs.org/genlayer-js/1.1.8":
            return json.dumps(
                {
                    "name": "genlayer-js",
                    "version": "1.1.8",
                    "repository": {
                        "type": "git",
                        "url": "git+https://github.com/yeagerai/genlayer-js.git",
                    },
                },
                sort_keys=True,
            )
        if url == "https://github.com/yeagerai/genlayer-js/blob/main/.releaseproof/ownership.json":
            return json.dumps(
                {
                    "package": "genlayer-js",
                    "repository": "https://github.com/yeagerai/genlayer-js",
                    "wallet": _GL.message.sender_address.lower(),
                },
                sort_keys=True,
            )
        if url == "https://github.com/yeagerai/genlayer-js/releases":
            return "Release genlayer-js v1.1.8 from yeagerai/genlayer-js"
        if url == "https://github.com/yeagerai/genlayer-js/blob/main/CHANGELOG.md":
            return "CHANGELOG: genlayer-js 1.1.8 includes Studio client release notes."
        raise AssertionError(f"unexpected web.render url: {url}")


class _Nondet:
    web = _NondetWeb()
    prompts = []

    @staticmethod
    def exec_prompt(prompt):
        _Nondet.prompts.append(prompt)
        if "binding_hash must be exactly" in prompt:
            marker = "binding_hash must be exactly '"
            binding_hash = prompt.split(marker, 1)[1].split("'", 1)[0]
            return json.dumps(
                {
                    "valid": True,
                    "repository_match": True,
                    "wallet_match": True,
                    "summary": "The npm registry and ownership proof bind genlayer-js to the expected repository and wallet.",
                    "binding_hash": binding_hash,
                },
                separators=(",", ":"),
            )
        if "evidence_bundle_hash: exactly" in prompt:
            marker = 'evidence_bundle_hash: exactly "'
            evidence_hash = prompt.split(marker, 1)[1].split('"', 1)[0]
            return json.dumps(
                {
                    "status": "verified",
                    "confidence": 91,
                    "version_match": True,
                    "tag_match": True,
                    "registry_match": True,
                    "changelog_match": True,
                    "risk_flags": [],
                    "evidence_bundle_hash": evidence_hash,
                    "summary": "GitHub, npm registry, and changelog evidence all support genlayer-js 1.1.8.",
                },
                separators=(",", ":"),
            )
        raise AssertionError("unexpected exec_prompt request")


class _VM:
    Return = _Return

    @staticmethod
    def run_nondet_unsafe(leader_fn, validator_fn):
        calldata = leader_fn()
        if validator_fn(_Return(calldata)) is not True:
            raise AssertionError("validator rejected leader calldata")
        return calldata


class _Contract:
    pass


class _Message:
    sender_address = "0x0000000000000000000000000000000000000000"


class _GL:
    Contract = _Contract
    public = _Public()
    vm = _VM()
    message = _Message()
    nondet = _Nondet()


class _DynArray(list):
    pass


class _TreeMap(dict):
    pass


def _install_genlayer_stub():
    module = types.ModuleType("genlayer")
    module.gl = _GL()
    module.DynArray = _DynArray
    module.TreeMap = _TreeMap
    module.u64 = int
    module.u8 = int
    sys.modules["genlayer"] = module


def _load_contract_module():
    spec = importlib.util.spec_from_file_location("release_proof_verifier", CONTRACT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main():
    source = CONTRACT_PATH.read_text(encoding="utf-8")
    if EXPECTED_DEPENDS not in source.splitlines()[0]:
        raise SystemExit(f"missing pinned runtime dependency: {EXPECTED_DEPENDS}")

    _install_genlayer_stub()
    module = _load_contract_module()
    contract_cls = module.ReleaseProofVerifier
    if not issubclass(contract_cls, _Contract):
        raise SystemExit("ReleaseProofVerifier must inherit gl.Contract")

    contract = _fresh_contract(contract_cls)
    required_methods = {
        "claim_publisher": "write",
        "verify_release": "write",
        "get_release_count": "view",
        "get_latest_release_id": "view",
        "get_release": "view",
        "list_release_ids": "view",
        "get_publisher_binding": "view",
    }
    for method_name, visibility in required_methods.items():
        method = getattr(contract, method_name, None)
        if method is None:
            raise SystemExit(f"missing method: {method_name}")
        actual = getattr(getattr(contract_cls, method_name), "__genlayer_visibility__", None)
        if actual != visibility:
            raise SystemExit(f"{method_name} must be public.{visibility}")

    release_id = module._release_id("npm:genlayer-js", "github:yeagerai/genlayer-js", "1.1.8")
    if not release_id.startswith("rel_") or len(release_id) != 24:
        raise SystemExit("release id format check failed")

    manifest = module._canonical_sources(
        "genlayer-js",
        "https://github.com/yeagerai/genlayer-js/releases",
        "https://www.npmjs.com/package/genlayer-js/v/1.1.8",
        "https://github.com/yeagerai/genlayer-js/blob/main/CHANGELOG.md",
    )
    if [item["source_type"] for item in manifest] != [
        "github_release",
        "package_registry",
        "changelog",
    ]:
        raise SystemExit("source manifest type check failed")
    if len({item["host"] for item in manifest}) < 2:
        raise SystemExit("source diversity check failed")

    publisher = module._canonical_github_repository("https://github.com/yeagerai/genlayer-js")
    proof = module._canonical_ownership_proof(
        "https://github.com/yeagerai/genlayer-js/blob/main/.releaseproof/ownership.json",
        publisher,
    )
    if proof["canonical_url"].endswith("ownership.json") is not True:
        raise SystemExit("ownership proof canonicalization failed")

    binding = {
        "valid": True,
        "repository_match": True,
        "wallet_match": True,
        "publisher_identity": "github:yeagerai/genlayer-js",
        "package_identity": "npm:genlayer-js",
    }
    if not module._binding_matches_release(
        binding, "github:yeagerai/genlayer-js", "npm:genlayer-js"
    ):
        raise SystemExit("valid publisher binding rejected")
    if module._binding_matches_release(
        binding, "github:yeagerai/genlayer-js", "npm:another-package"
    ):
        raise SystemExit("binding must reject a different npm package")
    required_guards = (
        'independent.get("valid") is True',
        'release_package_does_not_match_bound_publisher_package',
        'binding.get("package_identity") == package_identity',
    )
    if any(guard not in source for guard in required_guards):
        raise SystemExit("source binding guards are incomplete")

    _exercise_real_contract_flow(module, contract_cls)

    print("ReleaseProof contract check passed")


def _fresh_contract(contract_cls):
    contract = contract_cls()
    contract.release_ids = _DynArray()
    contract.releases = _TreeMap()
    contract.publisher_owners = _TreeMap()
    contract.publisher_bindings = _TreeMap()
    return contract


def _exercise_real_contract_flow(module, contract_cls):
    _NondetWeb.calls = []
    _Nondet.prompts = []
    _GL.message.sender_address = "0xE22D4Dc6865BD451411479D3A146EAFBd87D156B"
    contract = _fresh_contract(contract_cls)

    publisher_identity = contract.claim_publisher(
        "genlayer-js",
        "https://github.com/yeagerai/genlayer-js",
        "https://registry.npmjs.org/genlayer-js",
        "https://github.com/yeagerai/genlayer-js/blob/main/.releaseproof/ownership.json",
    )
    if publisher_identity != "github:yeagerai/genlayer-js":
        raise SystemExit("claim_publisher returned the wrong publisher identity")

    binding = json.loads(contract.get_publisher_binding(publisher_identity))
    if binding.get("package_identity") != "npm:genlayer-js":
        raise SystemExit("publisher binding did not persist npm package identity")
    if binding.get("claimed_by") != _GL.message.sender_address.lower():
        raise SystemExit("publisher binding did not persist claimant wallet")
    if binding.get("registry_render_url") != "https://registry.npmjs.org/genlayer-js":
        raise SystemExit("publisher claim did not use npm registry API render URL")
    if not binding.get("registry_snapshot_hash") or not binding.get("proof_snapshot_hash"):
        raise SystemExit("publisher claim did not persist evidence snapshot hashes")

    render_urls = [call["url"] for call in _NondetWeb.calls]
    if render_urls.count("https://registry.npmjs.org/genlayer-js") != 2:
        raise SystemExit("publisher claim did not execute leader and validator registry renders")
    if render_urls.count("https://github.com/yeagerai/genlayer-js/blob/main/.releaseproof/ownership.json") != 2:
        raise SystemExit("publisher claim did not execute leader and validator proof renders")
    if len([prompt for prompt in _Nondet.prompts if "publisher ownership binding" in prompt]) != 2:
        raise SystemExit("publisher claim did not execute leader and validator LLM adjudication")

    try:
        contract.verify_release(
            "another-package",
            "1.1.8",
            "https://github.com/yeagerai/genlayer-js/releases",
            "https://registry.npmjs.org/another-package/1.1.8",
            "https://github.com/yeagerai/genlayer-js/blob/main/CHANGELOG.md",
        )
    except Exception as exc:
        if "release_package_does_not_match_bound_publisher_package" not in str(exc):
            raise
    else:
        raise SystemExit("verify_release accepted a package outside the claimed binding")

    release_id = contract.verify_release(
        "genlayer-js",
        "1.1.8",
        "https://github.com/yeagerai/genlayer-js/releases",
        "https://registry.npmjs.org/genlayer-js/1.1.8",
        "https://github.com/yeagerai/genlayer-js/blob/main/CHANGELOG.md",
    )
    expected_release_id = module._release_id(
        "npm:genlayer-js", "github:yeagerai/genlayer-js", "1.1.8"
    )
    if release_id != expected_release_id:
        raise SystemExit("verify_release returned a non-deterministic release id")

    record = json.loads(contract.get_release(release_id))
    if record["accepted_write"]["release_id"] != release_id:
        raise SystemExit("release record does not bind accepted write to returned release id")
    if json.loads(record["publisher_binding"])["package_identity"] != "npm:genlayer-js":
        raise SystemExit("release record did not preserve the accepted publisher binding")


if __name__ == "__main__":
    main()
