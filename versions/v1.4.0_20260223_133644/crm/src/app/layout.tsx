import './globals.css'
import TopNav from '../components/TopNav'
export const metadata = { title: 'CRM | Empire' }
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><TopNav currentApp="CRM" currentPort={3007} />{children}</body></html>
}
