import './globals.css'
export const metadata = { title: '👥 Empire CRM', description: 'Customer Relationship Management' }
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>
}
