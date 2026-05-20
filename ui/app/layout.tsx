import './globals.css'
import { ThemeProvider } from 'next-themes'
import { Providers } from './providers'
import { Sidebar } from '@/components/layout/sidebar'
import type { Metadata } from 'next'
import type { ReactNode } from 'react'

export const metadata: Metadata = {
  title: 'AgentOps',
  description: 'Build → Diagnose → Evolve loop control surface',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-TW" suppressHydrationWarning>
      <body className="flex h-screen overflow-hidden bg-background text-foreground">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <Providers>
            <Sidebar />
            <main className="flex-1 overflow-y-auto p-card">{children}</main>
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  )
}
