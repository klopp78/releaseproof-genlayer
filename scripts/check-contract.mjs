import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const contractPath = resolve("contracts/release_proof_verifier.py");
const source = readFileSync(contractPath, "utf8");
const firstLine = source.split(/\r?\n/, 1)[0];
const expectedRuntime =
  "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6";

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function sha256(value) {
  return createHash("sha256").update(value, "utf8").digest("hex");
}

assert(
  firstLine.includes(expectedRuntime),
  `missing pinned runtime dependency: ${expectedRuntime}`,
);
assert(
  /class\s+ReleaseProofVerifier\s*\(\s*gl\.Contract\s*\)\s*:/.test(source),
  "ReleaseProofVerifier must inherit gl.Contract",
);
assert(!/class\s+ReleaseProofVerifier\s*\(\s*Contract\s*\)\s*:/.test(source), "undefined Contract base remains");
assert(!/gl\.get_webpage|gl\.exec_prompt|gl\.json_loads|gl\.json_dumps|gl\.msg/.test(source), "unsupported legacy gl APIs remain");

for (const method of [
  "verify_release",
  "get_release_count",
  "get_latest_release_id",
  "get_release",
  "list_release_ids",
]) {
  assert(new RegExp(`def\\s+${method}\\s*\\(`).test(source), `missing method: ${method}`);
}

assert(
  /@gl\.public\.write\s+def\s+verify_release/s.test(source),
  "verify_release must be decorated with @gl.public.write",
);

for (const method of [
  "get_release_count",
  "get_latest_release_id",
  "get_release",
  "list_release_ids",
]) {
  assert(
    new RegExp(`@gl\\.public\\.view\\s+def\\s+${method}\\s*\\(`, "s").test(source),
    `${method} must be decorated with @gl.public.view`,
  );
}

assert(/gl\.vm\.run_nondet_unsafe/.test(source), "missing GenLayer nondeterministic consensus gate");
assert(/gl\.nondet\.web\.render/.test(source), "missing GenLayer web render call");
assert(/gl\.nondet\.exec_prompt/.test(source), "missing GenLayer prompt call");

assert(/snapshot_commitments/.test(source), "contract must persist snapshot commitments");
assert(/canonical_sources/.test(source), "contract must canonicalize source identities");
assert(/registry_package_identity_mismatch/.test(source), "contract must bind registry URLs to package identity");
assert(/changelog_must_belong_to_release_publisher/.test(source), "contract must bind changelog to publisher identity");

const releaseId = `rel_${sha256("npm:genlayer-js|github:yeagerai/genlayer-js|1.1.8").slice(0, 20)}`;
assert(releaseId.length === 24, "release id format check failed");

console.log("ReleaseProof contract check passed");
