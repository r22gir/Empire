import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import "./globals.css";
// Gold theme (gold-standard docs palette, colors only): inert unless <html data-theme="gold">.
// Dark stays the default; users switch with the Dark/Gold toggle (ThemeToggle) or ?theme=gold|default.
import "./theme/gold-docs.generated.css";
import "./theme/gold-docs.css";
import "./theme/theme-toggle.css";
// Empire design system v3 (Max v3): tokens + shell, scoped to .v3 (client pages and PDFs unaffected).
import "./v3/tokens.css";
import "./v3/shell.css";
import { Inter, Inter_Tight, Playfair_Display, IBM_Plex_Mono } from "next/font/google";
import FamilyAuthGate from "./components/FamilyAuthGate";
import { I18nWrapper } from "./components/I18nWrapper";
import { appDescriptionFromEnv, appTitleFromEnv } from "./lib/appIdentity";
import { COMMAND_CENTER_DOCUMENT_TITLE, documentTitleForHost } from "./lib/luxeDocumentTitle";

const edition = (process.env.NEXT_PUBLIC_EMPIRE_EDITION || "").trim().toLowerCase();
const isFamilyEdition = edition === "amp" || edition === "maxine";
const htmlLang = isFamilyEdition ? "es" : "en";

// Self-hosted at build time by next/font; exposed as CSS variables used by v3/tokens.css.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const interTight = Inter_Tight({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-inter-tight", display: "swap" });
const playfair = Playfair_Display({ subsets: ["latin"], weight: ["400", "500", "600"], style: ["normal", "italic"], variable: "--font-playfair", display: "swap" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-plex-mono", display: "swap" });
const fontVars = `${inter.variable} ${interTight.variable} ${playfair.variable} ${plexMono.variable}`;

export async function generateMetadata(): Promise<Metadata> {
  if (isFamilyEdition) {
    // Family editions (Max-e / Maxine): own title, private (noindex), never Empire/Workroom wording.
    return {
      title: appTitleFromEnv(),
      description: appDescriptionFromEnv(),
      robots: { index: false, follow: false, noarchive: true },
    };
  }
  const headerList = await headers();
  const title = documentTitleForHost(headerList.get("host"));
  return {
    title,
    description: title === COMMAND_CENTER_DOCUMENT_TITLE
      ? "Empire AI-Powered Business Command Center"
      : "Empire Workroom designer intake",
  };
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  viewportFit: 'cover',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang={htmlLang} className={fontVars} suppressHydrationWarning>
      <head>
        <meta httpEquiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0" />
        <meta httpEquiv="Pragma" content="no-cache" />
        <meta httpEquiv="Expires" content="0" />
        <meta name="robots" content="noindex, nofollow, noarchive" />
        <script dangerouslySetInnerHTML={{ __html: `
          if('serviceWorker' in navigator){navigator.serviceWorker.getRegistrations().then(function(r){r.forEach(function(w){w.unregister()})});}
          if('caches' in window){caches.keys().then(function(n){n.forEach(function(k){caches.delete(k)})});}
        `}} />
        <script dangerouslySetInnerHTML={{ __html: `
          (function(){try{var q=new URLSearchParams(location.search).get('theme');
          if(q==='gold'){localStorage.setItem('empire.theme','gold');}else if(q==='default'||q==='cyber'){localStorage.removeItem('empire.theme');}
          if(localStorage.getItem('empire.theme')==='gold'){document.documentElement.setAttribute('data-theme','gold');}}catch(e){}})();
        `}} />
      </head>
      <body className="antialiased"><I18nWrapper><FamilyAuthGate>{children}</FamilyAuthGate></I18nWrapper></body>
    </html>
  );
}
