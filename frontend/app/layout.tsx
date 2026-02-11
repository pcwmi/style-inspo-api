import type { Metadata, Viewport } from 'next'
import './globals.css'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: 'Style Inspo — AI Styling Assistant',
  description: 'AI that knows your wardrobe, learns your taste, and helps you get dressed with confidence.',
  openGraph: {
    title: 'Style Inspo — AI Styling Assistant',
    description: 'AI that knows your wardrobe, learns your taste, and helps you get dressed with confidence.',
    images: ['/showcase/og-image.png'],
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}

