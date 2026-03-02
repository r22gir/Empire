import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'EmpireBox Founder Dashboard',
  description: 'AI-Powered Business Command Center',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
