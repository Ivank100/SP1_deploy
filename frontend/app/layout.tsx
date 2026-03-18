/**
 * This file defines the shared layout shell for the Next.js app.
 * It wraps all pages with global structure and metadata.
 */
import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'LectureSense - AI-Powered Lecture Q&A',
  description: 'Ask questions about your lecture materials with AI-powered answers and citations',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}

