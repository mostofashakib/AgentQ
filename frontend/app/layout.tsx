import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = { title: 'AgentQ Control Plane' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg text-text">
        {children}
      </body>
    </html>
  )
}
