import './globals.css'
export const metadata = { title: '📦 Empire Inventory', description: 'Inventory Management' }
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>
}
