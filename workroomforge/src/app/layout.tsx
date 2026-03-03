import './globals.css'
import TopNav from '../components/TopNav'
export const metadata = { title: 'WorkroomForge | Empire' }
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><head><script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js" async></script></head><body><TopNav currentApp="WorkroomForge" currentPort={3001} />{children}</body></html>
}
