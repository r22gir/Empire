import './globals.css'
export const metadata = { title: '💰 Empire Finance', description: 'Financial Management' }
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>
}
