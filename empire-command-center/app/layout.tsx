import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import "./globals.css";
// Gold theme (gold-standard docs palette, colors only): inert unless <html data-theme="gold">.
// Dark stays the default; users switch with the Dark/Gold toggle (ThemeToggle) or ?theme=gold|default.
import "./theme/gold-docs.generated.css";
import "./theme/gold-docs.css";
import "./theme/theme-toggle.css";
import { I18nWrapper } from "./components/I18nWrapper";
import { COMMAND_CENTER_DOCUMENT_TITLE, documentTitleForHost } from "./lib/luxeDocumentTitle";

export async function generateMetadata(): Promise<Metadata> {
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
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta httpEquiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0" />
        <meta httpEquiv="Pragma" content="no-cache" />
        <meta httpEquiv="Expires" content="0" />
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
      <body className="antialiased"><I18nWrapper>{children}</I18nWrapper></body>
    </html>
  );
}
