"use client";

import { useState } from "react";
import { readRelease, readReleaseCount, RELEASE_PROOF_CONTRACT_ADDRESS } from "@/lib/genlayer";

function pretty(value: unknown) {
  if (typeof value === "string") {
    try { return JSON.stringify(JSON.parse(value), null, 2); } catch { return value; }
  }
  return JSON.stringify(value, null, 2);
}

export default function ExplorerPage() {
  const [address, setAddress] = useState(RELEASE_PROOF_CONTRACT_ADDRESS);
  const [releaseId, setReleaseId] = useState("");
  const [result, setResult] = useState("");
  const [message, setMessage] = useState("Enter a release ID to inspect a consensus-backed record.");

  async function inspect() {
    if (!releaseId.trim()) return setMessage("A release ID is required.");
    try {
      setMessage("Reading contract storage...");
      const [count, release] = await Promise.all([
        readReleaseCount({ contractAddress: address as `0x${string}` }),
        readRelease(releaseId.trim(), { contractAddress: address as `0x${string}` }),
      ]);
      setResult(pretty(release));
      setMessage(`Loaded release ${releaseId.trim()} from a registry with ${String(count)} records.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
      setResult("");
    }
  }

  return <main className="mx-auto max-w-4xl px-5 py-10">
    <a className="pill" href="/">ReleaseProof</a>
    <h1 className="mt-7 text-4xl font-semibold">Release explorer</h1>
    <p className="mt-3 max-w-2xl text-lg text-[#52616d]">Inspect exact records written after GenLayer consensus. This view never calculates a verdict locally.</p>
    <section className="tool-panel mt-8 grid gap-4">
      <label className="field-label" htmlFor="address">Studio contract address</label>
      <input className="text-input" id="address" value={address} onChange={(e) => setAddress(e.target.value)} />
      <label className="field-label" htmlFor="release-id">Resolved release ID</label>
      <input className="text-input" id="release-id" placeholder="rel_..." value={releaseId} onChange={(e) => setReleaseId(e.target.value)} />
      <button className="action-button primary w-fit" onClick={inspect}>Load resolved case</button>
      <p className="text-sm text-[#52616d]">{message}</p>
    </section>
    {result ? <pre className="result-card mt-6 overflow-x-auto text-sm">{result}</pre> : null}
  </main>;
}
