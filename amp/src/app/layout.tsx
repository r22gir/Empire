import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AMP — Actitud Mental Positiva | Transforma Tu Mente, Transforma Tu Vida",
  description:
    "La plataforma #1 en español para desarrollo personal, liderazgo y bienestar mental. Meditaciones guiadas, retos de 21 días, y masterclass de liderazgo inspiradas en John Maxwell.",
  keywords: [
    "actitud mental positiva",
    "desarrollo personal",
    "liderazgo",
    "meditación",
    "bienestar mental",
    "mindset",
    "John Maxwell",
    "coaching",
    "crecimiento personal",
  ],
  openGraph: {
    title: "AMP — Actitud Mental Positiva",
    description:
      "Transforma tu mente, transforma tu vida. Desarrollo personal, liderazgo y bienestar mental en español.",
    url: "https://www.actitudmentalpositiva.com",
    siteName: "AMP",
    locale: "es_ES",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "AMP — Actitud Mental Positiva",
    description:
      "Transforma tu mente, transforma tu vida. La plataforma #1 en español para desarrollo personal.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="scroll-smooth">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
