import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'EmpireBox - Complete Reselling Business in a Box',
  description: 'Hardware bundles with MarketForge subscription for resellers',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
