import { RELEASE_PROOF_CONTRACT_ADDRESS } from "@/lib/genlayer";

const repoUrl = "https://github.com/klopp78/releaseproof-genlayer";
const studioUrl = `https://explorer-studio.genlayer.com/address/${RELEASE_PROOF_CONTRACT_ADDRESS}`;

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f5f7fb] text-[#15171a]">
      <section className="border-b border-[#d8dde8] bg-white">
        <div className="mx-auto max-w-6xl px-5 py-12 lg:px-8">
          <span className="pill">GenLayer Project</span>
          <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-tight md:text-6xl">ReleaseProof</h1>
          <p className="mt-5 max-w-3xl text-lg leading-8 text-[#52616d]">A consensus-backed release provenance workflow for software agents. Publishers bind ownership, users verify a release, and every accepted result can be inspected from the on-chain registry.</p>
          <div className="mt-7 flex flex-wrap gap-3"><a className="action-button primary" href="/claim">Claim publisher</a><a className="action-button" href="/verify">Verify release</a><a className="action-button" href="/explorer">Explore records</a></div>
        </div>
      </section>
      <section className="mx-auto grid max-w-6xl gap-5 px-5 py-8 md:grid-cols-3 lg:px-8">
        <article className="tool-panel"><span className="field-label">01 Publisher binding</span><h2 className="mt-2 text-2xl font-semibold">Claim ownership</h2><p className="mt-3 leading-7 text-[#52616d]">Bind a package to a GitHub repository and ownership proof through a Studio write accepted by GenLayer validators.</p><a className="mt-5 inline-block text-sm font-semibold text-[#155e75]" href="/claim">Open claim flow</a></article>
        <article className="tool-panel"><span className="field-label">02 Release check</span><h2 className="mt-2 text-2xl font-semibold">Verify evidence</h2><p className="mt-3 leading-7 text-[#52616d]">Submit GitHub, registry, and changelog sources. The app waits for a consensus receipt and returns its exact release ID.</p><a className="mt-5 inline-block text-sm font-semibold text-[#155e75]" href="/verify">Open verification flow</a></article>
        <article className="tool-panel"><span className="field-label">03 Public history</span><h2 className="mt-2 text-2xl font-semibold">Inspect records</h2><p className="mt-3 leading-7 text-[#52616d]">Read a resolved record directly from the deployed contract. No local keyword scoring or simulated verdicts are shown as consensus.</p><a className="mt-5 inline-block text-sm font-semibold text-[#155e75]" href="/explorer">Open explorer</a></article>
      </section>
      <footer className="mx-auto flex max-w-6xl flex-wrap gap-4 px-5 pb-10 text-sm text-[#52616d] lg:px-8"><a href={repoUrl} rel="noreferrer" target="_blank">Source repository</a><a href={studioUrl} rel="noreferrer" target="_blank">Studio contract</a><code>{RELEASE_PROOF_CONTRACT_ADDRESS}</code></footer>
    </main>
  );
}
