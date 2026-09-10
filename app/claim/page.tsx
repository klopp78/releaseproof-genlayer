"use client";

import { useState } from "react";
import { claimPublisher, RELEASE_PROOF_CONTRACT_ADDRESS, type WalletAddress } from "@/lib/genlayer";

declare global { interface Window { ethereum?: { request: (args: { method: string; params?: unknown[] }) => Promise<unknown> } } }

export default function ClaimPage() {
  const [packageName, setPackageName] = useState("genlayer-js");
  const [repositoryUrl, setRepositoryUrl] = useState("https://github.com/yeagerai/genlayer-js");
  const [registryUrl, setRegistryUrl] = useState("https://www.npmjs.com/package/genlayer-js");
  const [proofUrl, setProofUrl] = useState("https://github.com/yeagerai/genlayer-js/blob/main/.releaseproof/ownership.json");
  const [address, setAddress] = useState(RELEASE_PROOF_CONTRACT_ADDRESS);
  const [wallet, setWallet] = useState<WalletAddress | null>(null);
  const [message, setMessage] = useState("Connect a browser wallet to begin a publisher claim.");
  const [binding, setBinding] = useState("");
  const [busy, setBusy] = useState(false);
  async function connectWallet() { if (!window.ethereum) throw new Error("No browser wallet detected."); const accounts = await window.ethereum.request({ method: "eth_requestAccounts" }) as WalletAddress[]; if (!accounts[0]) throw new Error("No wallet account returned."); setWallet(accounts[0]); return accounts[0]; }
  async function submit() { try { setBusy(true); setMessage("Requesting wallet and waiting for GenLayer consensus..."); setBinding(""); const account = wallet ?? await connectWallet(); const result = await claimPublisher({ walletAddress: account, packageName, githubRepositoryUrl: repositoryUrl, registryUrl, ownershipProofUrl: proofUrl, contractAddress: address as `0x${string}` }); setBinding(typeof result.binding === "string" ? result.binding : JSON.stringify(result.binding, null, 2)); setMessage(`Publisher claim accepted: ${result.publisherIdentity}`); } catch (error) { setMessage(error instanceof Error ? error.message : String(error)); } finally { setBusy(false); } }
  return <main className="mx-auto min-h-screen max-w-3xl px-5 py-10 text-[#15171a]"><a className="pill" href="/">ReleaseProof</a><h1 className="mt-7 text-4xl font-semibold">Claim publisher ownership</h1><p className="mt-3 max-w-2xl text-lg leading-8 text-[#52616d]">Create the package-to-repository binding before release verification. This writes to the deployed Studio contract and waits for an accepted consensus receipt.</p><section className="tool-panel mt-8 grid gap-4"><Field id="package" label="Package name" value={packageName} setValue={setPackageName} /><Field id="repository" label="GitHub publisher repository" value={repositoryUrl} setValue={setRepositoryUrl} /><Field id="registry" label="Package registry URL" value={registryUrl} setValue={setRegistryUrl} /><Field id="proof" label="Repository ownership proof URL" value={proofUrl} setValue={setProofUrl} /><Field id="address" label="Studio contract address" value={address} setValue={setAddress} /><div className="flex flex-wrap gap-3"><button className="action-button" onClick={() => connectWallet().then(() => setMessage("Wallet connected.")).catch((error) => setMessage(error.message))}>Connect wallet</button><button className="action-button primary" disabled={busy} onClick={submit}>{busy ? "Awaiting consensus" : "Claim publisher"}</button></div><p className="text-sm text-[#52616d]">{message}</p></section>{binding ? <pre className="result-card mt-6 overflow-x-auto text-sm">{binding}</pre> : null}</main>;
}
function Field({ id, label, value, setValue }: { id: string; label: string; value: string; setValue: (value: string) => void }) { return <label className="grid gap-2" htmlFor={id}><span className="field-label">{label}</span><input className="text-input" id={id} value={value} onChange={(event) => setValue(event.target.value)} /></label>; }
