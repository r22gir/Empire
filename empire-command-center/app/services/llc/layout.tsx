import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "LLC Factory — Business Formation & Document Services | DC, MD, VA",
  description:
    "LLC formation, apostille, notary, and registered agent services for DC, Maryland & Virginia. Same-day filing. AI-powered documents. Bilingual EN/ES.",
  keywords: [
    "LLC formation",
    "apostille",
    "notary",
    "registered agent",
    "DC",
    "Maryland",
    "Virginia",
    "business formation",
    "EIN filing",
    "BOI report",
  ],
};

export default function LLCLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
