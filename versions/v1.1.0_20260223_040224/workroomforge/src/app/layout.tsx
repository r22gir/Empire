import './globals.css'
export const metadata = { title: 'WorkroomForge', description: 'Workroom Management' }
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body className="bg-[#1A1A1A]">{children}</body></html>
}
