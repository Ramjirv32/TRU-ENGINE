import './globals.css'

export const metadata = {
  title: 'University Program Search',
  description: 'Search for academic programs at universities',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
