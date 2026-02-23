import './globals.css'
import Sidebar from '@/components/Sidebar'

export const metadata = { title: 'Empire | Founders Edition' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-64">{children}</main>
      </body>
    </html>
  )
}
