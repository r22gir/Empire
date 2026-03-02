import './globals.css'
import TopNav from '../components/TopNav'

export const metadata = {
  title: 'MAX | Empire',
  description: 'AI Director',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <TopNav currentApp="MAX" currentPort={3009} />
        {children}
      </body>
    </html>
  )
}
