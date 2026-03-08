import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Empire Command Center",
  description: "Empire AI-Powered Business Command Center",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
