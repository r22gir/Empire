import './globals.css'
import TopNav from '../components/TopNav'
export const metadata = { title: 'Finance | Empire' }
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><TopNav currentApp="Finance" currentPort={3005} />{children}</body></html>
}
