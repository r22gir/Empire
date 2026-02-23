import './globals.css'
import TopNav from '../components/TopNav'
export const metadata = { title: 'Inventory | Empire' }
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><TopNav currentApp="Inventory" currentPort={3004} />{children}</body></html>
}
