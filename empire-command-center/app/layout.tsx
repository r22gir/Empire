import type { Metadata, Viewport } from "next";
import "./globals.css";
import { I18nWrapper } from "./components/I18nWrapper";

export const metadata: Metadata = {
  title: "Empire Command Center",
  description: "Empire AI-Powered Business Command Center",
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
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
