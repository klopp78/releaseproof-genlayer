import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

export const RELEASE_PROOF_CONTRACT_ADDRESS =
  "0x0000000000000000000000000000000000000000" as const;

export type WalletAddress = `0x${string}`;

export type ReleaseProofInput = {
  walletAddress: WalletAddress;
  packageName: string;
  version: string;
  githubReleaseUrl: string;
  registryUrl: string;
  changelogUrl: string;
};

export type ChainReadOptions = {
  walletAddress?: WalletAddress;
  contractAddress?: `0x${string}`;
};

export function createReleaseProofClient(walletAddress?: WalletAddress) {
  return createClient({
    chain: studionet,
    account: walletAddress,
  });
}

function releaseProofAddress(contractAddress?: `0x${string}`) {
  return contractAddress ?? RELEASE_PROOF_CONTRACT_ADDRESS;
}

export async function readReleaseCount(options: ChainReadOptions = {}) {
  const client = createReleaseProofClient(options.walletAddress);

  return client.readContract({
    address: releaseProofAddress(options.contractAddress),
    functionName: "get_release_count",
    args: [],
    jsonSafeReturn: true,
    leaderOnly: true,
  });
}

export async function readRelease(
  releaseId: string,
  options: ChainReadOptions = {},
) {
  const client = createReleaseProofClient(options.walletAddress);

  return client.readContract({
    address: releaseProofAddress(options.contractAddress),
    functionName: "get_release",
    args: [releaseId],
    jsonSafeReturn: true,
    leaderOnly: true,
  });
}

export async function submitReleaseProof({
  walletAddress,
  packageName,
  version,
  githubReleaseUrl,
  registryUrl,
  changelogUrl,
}: ReleaseProofInput) {
  const client = createReleaseProofClient(walletAddress);
  await client.connect("studionet");

  const hash = await client.writeContract({
    address: RELEASE_PROOF_CONTRACT_ADDRESS,
    functionName: "verify_release",
    args: [
      packageName,
      version,
      githubReleaseUrl,
      registryUrl,
      changelogUrl,
    ],
    value: BigInt(0),
    leaderOnly: false,
  });

  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.ACCEPTED,
    fullTransaction: true,
  });

  const releaseId = releaseIdFromReceipt(receipt);
  const release = await readRelease(releaseId, {
    walletAddress,
  });

  return { hash, receipt, releaseId, release };
}

function releaseIdFromReceipt(receipt: unknown): string {
  const candidates = collectStrings(receipt);
  const releaseId = candidates
    .map((value) => value.match(/rel_[a-f0-9]{20}/)?.[0])
    .find((value): value is string => Boolean(value));

  if (!releaseId) {
    throw new Error("Accepted transaction did not return a release ID.");
  }

  return releaseId;
}

function collectStrings(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (!value || typeof value !== "object") return [];
  return Object.values(value as Record<string, unknown>).flatMap(collectStrings);
}
