import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { TransactionStatus } from "genlayer-js/types";

export const RELEASE_PROOF_CONTRACT_ADDRESS =
  (process.env.NEXT_PUBLIC_RELEASE_PROOF_CONTRACT_ADDRESS ??
    "0x4d7a0835aE34aE5F1C53c3cC984aF861Dc2C5219") as `0x${string}`;

export type WalletAddress = `0x${string}`;

export type ReleaseProofInput = {
  walletAddress: WalletAddress;
  packageName: string;
  version: string;
  githubReleaseUrl: string;
  registryUrl: string;
  changelogUrl: string;
  contractAddress?: `0x${string}`;
};

export type PublisherClaimInput = {
  walletAddress: WalletAddress;
  packageName: string;
  githubRepositoryUrl: string;
  registryUrl: string;
  ownershipProofUrl: string;
  contractAddress?: `0x${string}`;
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

export async function readPublisherBinding(
  publisherIdentity: string,
  options: ChainReadOptions = {},
) {
  const client = createReleaseProofClient(options.walletAddress);
  return client.readContract({
    address: releaseProofAddress(options.contractAddress),
    functionName: "get_publisher_binding",
    args: [publisherIdentity],
    jsonSafeReturn: true,
    leaderOnly: true,
  });
}

export async function claimPublisher({
  walletAddress,
  packageName,
  githubRepositoryUrl,
  registryUrl,
  ownershipProofUrl,
  contractAddress,
}: PublisherClaimInput) {
  const client = createReleaseProofClient(walletAddress);
  await client.connect("studionet");
  const address = releaseProofAddress(contractAddress);
  const hash = await client.writeContract({
    address,
    functionName: "claim_publisher",
    args: [packageName, githubRepositoryUrl, registryUrl, ownershipProofUrl],
    value: BigInt(0),
    leaderOnly: false,
  });
  const receipt = await client.waitForTransactionReceipt({
    hash,
    status: TransactionStatus.ACCEPTED,
    fullTransaction: true,
  });
  const publisherIdentity = publisherIdentityFromReceipt(receipt);
  const binding = await readPublisherBinding(publisherIdentity, {
    walletAddress,
    contractAddress: address,
  });
  return { hash, receipt, publisherIdentity, binding };
}

export async function submitReleaseProof({
  walletAddress,
  packageName,
  version,
  githubReleaseUrl,
  registryUrl,
  changelogUrl,
  contractAddress,
}: ReleaseProofInput) {
  const client = createReleaseProofClient(walletAddress);
  await client.connect("studionet");
  const address = releaseProofAddress(contractAddress);

  const hash = await client.writeContract({
    address,
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
    contractAddress: address,
  });

  return { hash, receipt, releaseId, release };
}

function publisherIdentityFromReceipt(receipt: unknown): string {
  const candidates = collectStrings(receipt);
  const publisher = candidates
    .map((value) => value.match(/github:[a-z0-9_.-]+\/[a-z0-9_.-]+/)?.[0])
    .find((value): value is string => Boolean(value));
  if (!publisher) {
    throw new Error("Accepted publisher claim did not return an identity.");
  }
  return publisher;
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
