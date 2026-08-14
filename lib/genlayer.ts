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

export async function readLatestReleaseId(options: ChainReadOptions = {}) {
  const client = createReleaseProofClient(options.walletAddress);

  return client.readContract({
    address: releaseProofAddress(options.contractAddress),
    functionName: "get_latest_release_id",
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
  });

  const latestReleaseId = await readLatestReleaseId({ walletAddress });
  const release = await readRelease(String(latestReleaseId), {
    walletAddress,
  });

  return { hash, receipt, latestReleaseId: String(latestReleaseId), release };
}
