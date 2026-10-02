import type { Metadata, Viewport } from "next";
import "./globals.css";
import { I18nWrapper } from "./components/I18nWrapper";
import { appDescriptionFromEnv, appTitleFromEnv } from "./lib/appIdentity";

const edition = (process.env.NEXT_PUBLIC_EMPIRE_EDITION || "").trim().toLowerCase();
const htmlLang = edition === "amp" || edition === "maxine" ? "es" : "en";

export const metadata: Metadata = {
  title: appTitleFromEnv(),
  description: appDescriptionFromEnv(),
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  viewportFit: 'cover',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang={htmlLang}>
      <head>
        <meta httpEquiv="Cache-Control" content="no-store, no-cache, must-revalidate, max-age=0" />
        <meta httpEquiv="Pragma" content="no-cache" />
        <meta httpEquiv="Expires" content="0" />
        <script dangerouslySetInnerHTML={{ __html: `
          if('serviceWorker' in navigator){navigator.serviceWorker.getRegistrations().then(function(r){r.forEach(function(w){w.unregister()})});}
          if('caches' in window){caches.keys().then(function(n){n.forEach(function(k){caches.delete(k)})});}
        `}} />
      </head>
      <body className="antialiased"><I18nWrapper>{children}</I18nWrapper></body>
    </html>
  );
}
