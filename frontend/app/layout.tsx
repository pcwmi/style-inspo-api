import type { Metadata, Viewport } from 'next'
import './globals.css'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: 'Mira — your stylist friend',
  description: 'Text her what you\'re wearing. She knows your closet, your taste, and texts back.',
  openGraph: {
    title: 'Mira — your stylist friend',
    description: 'Text her what you\'re wearing. She knows your closet, your taste, and texts back.',
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

