import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AMP — El Portal de la Alegría | Actitud Mental Positiva",
  description: "Transforma tu mente, transforma tu vida. Plataforma en español para desarrollo personal, meditación guiada, bienestar y liderazgo. Tu portal de la alegría.",
  keywords: ["actitud mental positiva", "portal de la alegría", "meditación", "bienestar", "liderazgo", "desarrollo personal", "mentalidad"],
  openGraph: {
    title: "AMP — El Portal de la Alegría",
    description: "Transforma tu mente, transforma tu vida. Meditación, bienestar y liderazgo en español.",
    url: "https://www.actitudmentalpositiva.com",
    siteName: "AMP — Actitud Mental Positiva",
    locale: "es_ES",
    type: "website",
  },
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#D4A030",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="scroll-smooth">
      <body className="antialiased min-h-screen">{children}</body>
    </html>
  );
}
