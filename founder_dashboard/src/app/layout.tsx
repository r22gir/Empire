import './globals.css'

export const metadata = {
  title: 'MAX | Empire',
  description: 'AI Director',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/4.0.0/model-viewer.min.js" async></script>
      </head>
      <body>
        {children}
      </body>
    </html>
  )
}
