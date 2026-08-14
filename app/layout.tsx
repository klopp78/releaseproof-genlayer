import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://klopp78.github.io/releaseproof-genlayer/"),
  title: "ReleaseProof for GenLayer",
  description:
    "A GenLayer-powered tool for verifying software release provenance across GitHub, registries, and changelogs.",
  openGraph: {
    title: "ReleaseProof for GenLayer",
    description:
      "Consensus-backed release provenance for open-source software packages.",
    images: [
      {
        url: "/og.png",
        width: 1200,
        height: 630,
        alt: "ReleaseProof for GenLayer social preview",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "ReleaseProof for GenLayer",
    description:
      "Consensus-backed release provenance for open-source software packages.",
    images: ["/og.png"],
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
