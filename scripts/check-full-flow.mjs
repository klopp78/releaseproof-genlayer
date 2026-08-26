import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const client = await readFile(resolve(root, "lib/genlayer.ts"), "utf8");
const page = await readFile(resolve(root, "app/page.tsx"), "utf8");

for (const required of [
  "function claimPublisher",
  "function readPublisherBinding",
  "function submitReleaseProof",
  "function releaseIdFromReceipt",
  "readRelease(releaseId",
  "function publisherIdentityFromReceipt",
  "claim_publisher",
  "verify_release",
]) {
  if (!client.includes(required)) throw new Error(`Missing client flow step: ${required}`);
}

for (const required of [
  "submitPublisherClaim",
  "Claim publisher",
  "contractAddress",
  "submitRelease",
  "Read release ID",
]) {
  if (!page.includes(required)) throw new Error(`Missing UI flow step: ${required}`);
}

console.log("ReleaseProof full two-step client flow check passed");
