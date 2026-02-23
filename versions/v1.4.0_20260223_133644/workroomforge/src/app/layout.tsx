import './globals.css'
import TopNav from '../components/TopNav'
export const metadata = { title: 'WorkroomForge | Empire' }
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><TopNav currentApp="WorkroomForge" currentPort={3001} />{children}</body></html>
}
