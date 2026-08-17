"use client";

import { useMemo, useState } from "react";
import {
  readRelease,
  readReleaseCount,
  RELEASE_PROOF_CONTRACT_ADDRESS,
  submitReleaseProof,
  type WalletAddress,
} from "@/lib/genlayer";

const repoUrl = "https://github.com/klopp78/releaseproof-genlayer";
const liveUrl = "https://klopp78.github.io/releaseproof-genlayer/";
const explorerUrl = `https://explorer-studio.genlayer.com/address/${RELEASE_PROOF_CONTRACT_ADDRESS}`;

type ChainStatus =
  | "idle"
  | "connecting"
  | "reading"
  | "submitting"
  | "accepted"
  | "error";

type ReleaseRecord = {
  schema_version?: string;
  release_id?: string;
  package_name?: string;
  version?: string;
  package_identity?: string;
  publisher_identity?: string;
  submitted_by?: string;
  source_manifest?: {
    source_type?: string;
    host?: string;
    url_hash?: string;
    canonical_url?: string;
  }[];
  snapshot_commitments?: {
    source_type?: string;
    host?: string;
    canonical_url?: string;
    package_identity?: string;
    publisher_identity?: string;
    url_hash?: string;
    snapshot_hash?: string;
    snapshot_chars?: number;
  }[];
  evidence_bundle_hash?: string;
  accepted_write?: {
    release_id?: string;
    registry_sequence?: number;
    evidence_bundle_hash?: string;
  };
  result?: {
    status?: string;
    confidence?: number;
    version_match?: boolean;
    tag_match?: boolean;
    registry_match?: boolean;
    changelog_match?: boolean;
    risk_flags?: string[];
    evidence_bundle_hash?: string;
    summary?: string;
  };
};

declare global {
  interface Window {
    ethereum?: {
      request: (args: {
        method: string;
        params?: unknown[];
      }) => Promise<unknown>;
    };
  }
}

const examples = [
  {
    name: "genlayer-js",
    version: "1.1.8",
    github:
      "https://github.com/yeagerai/genlayer-js/releases",
    registry: "https://www.npmjs.com/package/genlayer-js/v/1.1.8",
    changelog:
      "https://github.com/yeagerai/genlayer-js/blob/main/CHANGELOG.md",
  },
  {
    name: "next",
    version: "16.2.6",
    github: "https://github.com/vercel/next.js/releases",
    registry: "https://www.npmjs.com/package/next/v/16.2.6",
    changelog: "https://github.com/vercel/next.js/releases",
  },
];

function parseRecord(value: unknown): ReleaseRecord | null {
  if (!value) return null;
  if (typeof value === "object") return value as ReleaseRecord;
  if (typeof value !== "string") return null;

  try {
    return JSON.parse(value) as ReleaseRecord;
  } catch {
    return null;
  }
}

function shortHash(value?: string) {
  if (!value) return "pending";
  if (value.length <= 18) return value;
  return `${value.slice(0, 10)}...${value.slice(-6)}`;
}

function statusLabel(status: ChainStatus) {
  switch (status) {
    case "connecting":
      return "Connecting wallet";
    case "reading":
      return "Reading registry";
    case "submitting":
      return "Awaiting consensus";
    case "accepted":
      return "Accepted";
    case "error":
      return "Needs attention";
    default:
      return "Ready";
  }
}

export default function Home() {
  const [packageName, setPackageName] = useState(examples[0].name);
  const [version, setVersion] = useState(examples[0].version);
  const [githubReleaseUrl, setGithubReleaseUrl] = useState(examples[0].github);
  const [registryUrl, setRegistryUrl] = useState(examples[0].registry);
  const [changelogUrl, setChangelogUrl] = useState(examples[0].changelog);
  const [walletAddress, setWalletAddress] = useState<WalletAddress | null>(
    null,
  );
  const [status, setStatus] = useState<ChainStatus>("idle");
  const [message, setMessage] = useState("");
  const [releaseCount, setReleaseCount] = useState<string>("not read");
  const [releaseId, setReleaseId] = useState("");
  const [record, setRecord] = useState<ReleaseRecord | null>(null);

  const hosts = useMemo(() => {
    return [githubReleaseUrl, registryUrl, changelogUrl].map((url) => {
      try {
        return new URL(url).host;
      } catch {
        return "invalid-url";
      }
    });
  }, [githubReleaseUrl, registryUrl, changelogUrl]);

  const canSubmit =
    packageName.trim().length >= 3 &&
    version.trim().length > 0 &&
    [githubReleaseUrl, registryUrl, changelogUrl].every((url) =>
      url.startsWith("https://"),
    );

  async function connectWallet() {
    if (!window.ethereum) {
      setStatus("error");
      setMessage("No browser wallet detected.");
      return null;
    }

    setStatus("connecting");
    const accounts = (await window.ethereum.request({
      method: "eth_requestAccounts",
    })) as WalletAddress[];
    const account = accounts[0];
    setWalletAddress(account);
    setStatus("idle");
    return account;
  }

  async function readById() {
    const account = walletAddress ?? (await connectWallet());
    if (!account) return;
    if (!releaseId.trim()) {
      setStatus("error");
      setMessage("Enter a release ID returned by a submitted transaction.");
      return;
    }

    try {
      setStatus("reading");
      setMessage("");
      const count = await readReleaseCount({ walletAddress: account });
      setReleaseCount(String(count));
      const storedRelease = await readRelease(releaseId.trim(), {
        walletAddress: account,
      });
      setRecord(parseRecord(storedRelease));
      setStatus("accepted");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  async function submitRelease() {
    const account = walletAddress ?? (await connectWallet());
    if (!account) return;

    try {
      setStatus("submitting");
      setMessage("");
      const result = await submitReleaseProof({
        walletAddress: account,
        packageName,
        version,
        githubReleaseUrl,
        registryUrl,
        changelogUrl,
      });
      setRecord(parseRecord(result.release));
      setReleaseId(result.releaseId);
      setStatus("accepted");
      setMessage(`Consensus accepted release ID ${result.releaseId}`);
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : String(error));
    }
  }

  function loadExample(index: number) {
    const example = examples[index];
    setPackageName(example.name);
    setVersion(example.version);
    setGithubReleaseUrl(example.github);
    setRegistryUrl(example.registry);
    setChangelogUrl(example.changelog);
  }

  return (
    <main className="min-h-screen bg-[#f5f7fb] text-[#15171a]">
      <section className="border-b border-[#d8dde8] bg-[#ffffff]">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 py-8 lg:grid-cols-[1.1fr_0.9fr] lg:px-8">
          <div>
            <div className="mb-5 flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-[0.16em] text-[#48606f]">
              <span>ReleaseProof</span>
              <span className="h-1 w-1 rounded-full bg-[#8aa1ad]" />
              <span>GenLayer Project</span>
            </div>
            <h1 className="max-w-3xl text-4xl font-semibold leading-tight md:text-6xl">
              Verify software releases before agents depend on them.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-[#52616d]">
              ReleaseProof checks whether a GitHub release, package registry,
              and changelog agree on the same package version. GenLayer
              validators read the evidence and store a compact provenance
              verdict instead of a bulky report.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <a className="pill" href={repoUrl} rel="noreferrer" target="_blank">
                GitHub repo
              </a>
              <a className="pill" href={liveUrl} rel="noreferrer" target="_blank">
                Live page
              </a>
              <a
                className="pill"
                href={explorerUrl}
                rel="noreferrer"
                target="_blank"
              >
                Explorer
              </a>
            </div>
          </div>

          <div className="release-map" aria-label="Release provenance map">
            <div>
              <span>GitHub tag</span>
              <strong>{hosts[0]}</strong>
            </div>
            <div>
              <span>Registry version</span>
              <strong>{hosts[1]}</strong>
            </div>
            <div>
              <span>Changelog</span>
              <strong>{hosts[2]}</strong>
            </div>
            <div>
              <span>Consensus record</span>
              <strong>{(record?.release_id ?? releaseId) || "not written yet"}</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[0.95fr_1.05fr] lg:px-8">
        <div className="tool-panel">
          <div className="mb-5 flex flex-wrap gap-2">
            <button className="action-button" onClick={() => loadExample(0)}>
              genlayer-js example
            </button>
            <button className="action-button" onClick={() => loadExample(1)}>
              next.js example
            </button>
          </div>

          <label className="field-label" htmlFor="package-name">
            Package
          </label>
          <input
            className="text-input mb-4 w-full"
            id="package-name"
            onChange={(event) => setPackageName(event.target.value)}
            value={packageName}
          />

          <label className="field-label" htmlFor="version">
            Version
          </label>
          <input
            className="text-input mb-4 w-full"
            id="version"
            onChange={(event) => setVersion(event.target.value)}
            value={version}
          />

          <label className="field-label" htmlFor="github-release">
            GitHub release or tags
          </label>
          <input
            className="text-input mb-4 w-full"
            id="github-release"
            onChange={(event) => setGithubReleaseUrl(event.target.value)}
            value={githubReleaseUrl}
          />

          <label className="field-label" htmlFor="registry-url">
            Package registry
          </label>
          <input
            className="text-input mb-4 w-full"
            id="registry-url"
            onChange={(event) => setRegistryUrl(event.target.value)}
            value={registryUrl}
          />

          <label className="field-label" htmlFor="changelog-url">
            Changelog or docs
          </label>
          <input
            className="text-input mb-5 w-full"
            id="changelog-url"
            onChange={(event) => setChangelogUrl(event.target.value)}
            value={changelogUrl}
          />

          <label className="field-label" htmlFor="release-id">
            Stored release ID
          </label>
          <input
            className="text-input mb-5 w-full"
            id="release-id"
            onChange={(event) => setReleaseId(event.target.value)}
            placeholder="Returned after a successful transaction"
            value={releaseId}
          />

          <div className="grid gap-3 sm:grid-cols-3">
            <button className="action-button" onClick={connectWallet}>
              Connect wallet
            </button>
            <button className="action-button" onClick={readById}>
              Read release ID
            </button>
            <button
              className="action-button primary"
              disabled={!canSubmit || status === "submitting"}
              onClick={submitRelease}
            >
              Verify release
            </button>
          </div>

          <p className="mt-4 text-sm text-[#60707b]">
            Contract address is intentionally isolated in one constant so the
            deployed Studio address can be swapped without changing app logic.
          </p>
        </div>

        <div className="grid gap-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="metric">
              <span>Status</span>
              <strong>{statusLabel(status)}</strong>
            </div>
            <div className="metric">
              <span>Registry count</span>
              <strong>{releaseCount}</strong>
            </div>
            <div className="metric">
              <span>Wallet</span>
              <strong>{walletAddress ? shortHash(walletAddress) : "not connected"}</strong>
            </div>
          </div>

          <div className="result-card">
            <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
              <div>
                <span className="field-label">Consensus result</span>
                <h2 className="text-2xl font-semibold">
                  {record?.package_name ?? packageName}@{record?.version ?? version}
                </h2>
              </div>
              <div className="confidence">
                <span>{record?.result?.confidence ?? "--"}</span>
                <small>/100</small>
              </div>
            </div>

            <div className="mb-5 grid gap-3 sm:grid-cols-2">
              <div className="info-tile">
                <span>Verdict</span>
                <strong>{record?.result?.status ?? "waiting for consensus"}</strong>
              </div>
              <div className="info-tile">
              <span>Evidence bundle</span>
                <strong>{shortHash(record?.evidence_bundle_hash ?? record?.result?.evidence_bundle_hash)}</strong>
              </div>
            </div>

            <p className="mb-5 leading-7 text-[#52616d]">
              {record?.result?.summary ??
                "The app does not calculate a local verdict. A submitted release is stored only after GenLayer validators compare the release, registry, and changelog evidence."}
            </p>

            <div className="mb-5 grid gap-2 sm:grid-cols-4">
              {[
                ["Version", record?.result?.version_match],
                ["Tag", record?.result?.tag_match],
                ["Registry", record?.result?.registry_match],
                ["Changelog", record?.result?.changelog_match],
              ].map(([label, value]) => (
                <div className="check-tile" key={String(label)}>
                  <span>{label}</span>
                  <strong>{value === undefined ? "pending" : value ? "match" : "miss"}</strong>
                </div>
              ))}
            </div>

            <div className="space-y-2">
              {(record?.snapshot_commitments ?? []).map((source) => (
                <div className="evidence-row" key={source.source_type}>
                  <span>{source.source_type}</span>
                  <strong>{source.host}</strong>
                  <code>{shortHash(source.snapshot_hash)}</code>
                </div>
              ))}
              {record?.snapshot_commitments?.length ? null : (
                <div className="evidence-row">
                  <span>snapshot commitments</span>
                  <strong>stored by contract</strong>
                  <code>snapshot hashes pending</code>
                </div>
              )}
            </div>

            {message ? <p className="mt-4 text-sm text-[#9a3d2f]">{message}</p> : null}
          </div>
        </div>
      </section>
    </main>
  );
}
