import assert from "node:assert/strict";

const walletAddress = "0xE22D4Dc6865BD451411479D3A146EAFBd87D156B";
const publisherIdentity = "github:yeagerai/genlayer-js";
const releaseId = "rel_61cf6c1ba558b13b129b";

class StudioFlowSimulator {
  constructor() {
    this.calls = [];
    this.publisherBindings = new Map();
    this.releases = new Map();
  }

  async writeContract({ functionName, args }) {
    this.calls.push({ kind: "write", functionName, args });
    if (functionName === "claim_publisher") {
      const [packageName, repositoryUrl, registryUrl, proofUrl] = args;
      assert.equal(packageName, "genlayer-js");
      assert.equal(repositoryUrl, "https://github.com/yeagerai/genlayer-js");
      assert.match(registryUrl, /npmjs\.com\/package\/genlayer-js/);
      assert.match(proofUrl, /\.releaseproof\/ownership\.json$/);
      this.publisherBindings.set(publisherIdentity, {
        publisher_identity: publisherIdentity,
        package_identity: "npm:genlayer-js",
        claimed_by: walletAddress.toLowerCase(),
      });
      return "0xpublisherclaim";
    }
    if (functionName === "verify_release") {
      const [packageName, version, releaseUrl, registryUrl, changelogUrl] = args;
      assert.equal(packageName, "genlayer-js");
      assert.equal(version, "1.1.8");
      assert.match(releaseUrl, /github\.com\/yeagerai\/genlayer-js\/releases/);
      assert.match(registryUrl, /npmjs\.com\/package\/genlayer-js/);
      assert.match(changelogUrl, /github\.com\/yeagerai\/genlayer-js/);
      assert.ok(this.publisherBindings.has(publisherIdentity));
      this.releases.set(releaseId, {
        release_id: releaseId,
        package_name: packageName,
        version,
        publisher_identity: publisherIdentity,
        accepted_write: { release_id: releaseId },
      });
      return "0xreleaseverification";
    }
    throw new Error(`Unexpected write ${functionName}`);
  }

  async waitForTransactionReceipt({ hash }) {
    this.calls.push({ kind: "receipt", hash });
    if (hash === "0xpublisherclaim") return { txExecutionResult: publisherIdentity };
    if (hash === "0xreleaseverification") return { txExecutionResult: releaseId };
    throw new Error(`Unknown transaction ${hash}`);
  }

  async readContract({ functionName, args }) {
    this.calls.push({ kind: "read", functionName, args });
    if (functionName === "get_publisher_binding") {
      return JSON.stringify(this.publisherBindings.get(args[0]) ?? {});
    }
    if (functionName === "get_release") {
      return JSON.stringify(this.releases.get(args[0]) ?? {});
    }
    throw new Error(`Unexpected read ${functionName}`);
  }
}

function receiptString(receipt, pattern, label) {
  const value = Object.values(receipt).find(
    (candidate) => typeof candidate === "string" && pattern.test(candidate),
  );
  assert.ok(value, `Accepted ${label} receipt must contain its returned identifier`);
  return value;
}

async function runFullFlow(client) {
  const publisherHash = await client.writeContract({
    functionName: "claim_publisher",
    args: [
      "genlayer-js",
      "https://github.com/yeagerai/genlayer-js",
      "https://www.npmjs.com/package/genlayer-js",
      "https://github.com/yeagerai/genlayer-js/blob/main/.releaseproof/ownership.json",
    ],
  });
  const publisherReceipt = await client.waitForTransactionReceipt({ hash: publisherHash });
  const returnedPublisher = receiptString(
    publisherReceipt,
    /^github:[a-z0-9_.-]+\/[a-z0-9_.-]+$/,
    "publisher claim",
  );
  const binding = JSON.parse(await client.readContract({
    functionName: "get_publisher_binding",
    args: [returnedPublisher],
  }));
  assert.equal(binding.publisher_identity, returnedPublisher);
  assert.equal(binding.package_identity, "npm:genlayer-js");
  assert.equal(binding.claimed_by, walletAddress.toLowerCase());

  const releaseHash = await client.writeContract({
    functionName: "verify_release",
    args: [
      "genlayer-js",
      "1.1.8",
      "https://github.com/yeagerai/genlayer-js/releases",
      "https://www.npmjs.com/package/genlayer-js/v/1.1.8",
      "https://github.com/yeagerai/genlayer-js/blob/main/CHANGELOG.md",
    ],
  });
  const releaseReceipt = await client.waitForTransactionReceipt({ hash: releaseHash });
  const returnedReleaseId = receiptString(
    releaseReceipt,
    /^rel_[a-f0-9]{20}$/,
    "release verification",
  );
  const release = JSON.parse(await client.readContract({
    functionName: "get_release",
    args: [returnedReleaseId],
  }));
  assert.equal(release.release_id, returnedReleaseId);
  assert.equal(release.accepted_write.release_id, returnedReleaseId);
  assert.equal(release.publisher_identity, returnedPublisher);
  return { returnedPublisher, returnedReleaseId };
}

const simulator = new StudioFlowSimulator();
const outcome = await runFullFlow(simulator);
assert.deepEqual(
  simulator.calls.map((call) => `${call.kind}:${call.functionName ?? call.hash}`),
  [
    "write:claim_publisher",
    "receipt:0xpublisherclaim",
    "read:get_publisher_binding",
    "write:verify_release",
    "receipt:0xreleaseverification",
    "read:get_release",
  ],
);
assert.equal(outcome.returnedPublisher, publisherIdentity);
assert.equal(outcome.returnedReleaseId, releaseId);
console.log("ReleaseProof simulated full-flow check passed");
