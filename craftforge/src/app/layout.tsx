import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CraftForge — CNC & 3D Print Business",
  description: "Full QuickBooks-level business management for woodwork, CNC, and 3D printing",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
