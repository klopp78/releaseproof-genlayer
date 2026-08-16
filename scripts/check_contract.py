import importlib.util
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


class _VM:
    Return = _Return

    @staticmethod
    def run_nondet_unsafe(leader_fn, validator_fn):
        return leader_fn()


class _Contract:
    pass


class _Message:
    sender_address = "0x0000000000000000000000000000000000000000"


class _GL:
    Contract = _Contract
    public = _Public()
    vm = _VM()
    message = _Message()


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

    contract = contract_cls()
    required_methods = {
        "verify_release": "write",
        "get_release_count": "view",
        "get_latest_release_id": "view",
        "get_release": "view",
        "list_release_ids": "view",
    }
    for method_name, visibility in required_methods.items():
        method = getattr(contract, method_name, None)
        if method is None:
            raise SystemExit(f"missing method: {method_name}")
        actual = getattr(getattr(contract_cls, method_name), "__genlayer_visibility__", None)
        if actual != visibility:
            raise SystemExit(f"{method_name} must be public.{visibility}")

    release_id = module._release_id("genlayer-js", "1.1.8")
    if not release_id.startswith("rel_") or len(release_id) != 24:
        raise SystemExit("release id format check failed")

    manifest = module._source_manifest(
        [
            "https://github.com/yeagerai/genlayer-js/releases",
            "https://www.npmjs.com/package/genlayer-js/v/1.1.8",
            "https://github.com/yeagerai/genlayer-js/blob/main/CHANGELOG.md",
        ]
    )
    if [item["source_type"] for item in manifest] != [
        "github_release",
        "package_registry",
        "changelog",
    ]:
        raise SystemExit("source manifest type check failed")
    if len({item["host"] for item in manifest}) < 2:
        raise SystemExit("source diversity check failed")

    print("ReleaseProof contract check passed")


if __name__ == "__main__":
    main()
