import type { Metadata, Viewport } from "next";
import "./globals.css";
import { ThemeProvider } from "@/context/ThemeContext";
import { AudioProvider } from "@/context/AudioContext";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import GlobalAudioPlayer from "@/components/GlobalAudioPlayer";
import MobileBottomNav from "@/components/MobileBottomNav";

export const metadata: Metadata = {
  title: "AMP — El Portal de la Alegría | Actitud Mental Positiva · Juan Diego Giraldo",
  description: "Transforma tu mente, transforma tu vida. El nuevo portal en español de Actitud Mental Positiva: meditaciones guiadas, check-in diario de ánimo, coaching y membresía.",
  keywords: [
    "actitud mental positiva",
    "el portal de la alegria",
    "juan diego giraldo",
    "meditacion en espanol",
    "bienestar",
    "crecimiento personal",
    "mindfulness"
  ],
  openGraph: {
    title: "AMP — El Portal de la Alegría",
    description: "Herramientas reales para transformar tu mente, un día a la vez. Meditaciones guiadas y coaching en español.",
    url: "https://www.actitudmentalpositiva.com",
    siteName: "Actitud Mental Positiva",
    locale: "es_ES",
    type: "website",
  },
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#E0A526",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="scroll-smooth">
      <body className="antialiased min-h-screen flex flex-col bg-[#FFFDF9] dark:bg-[#0E0C1C] text-[#1E1A17] dark:text-[#F6F3EE] transition-colors duration-300">
        <ThemeProvider>
          <AudioProvider>
            <SiteHeader />
            <main className="flex-1 pb-20 md:pb-24">
              {children}
            </main>
            <SiteFooter />
            <GlobalAudioPlayer />
            <MobileBottomNav />
          </AudioProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
