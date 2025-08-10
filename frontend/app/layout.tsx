import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ToastProvider } from '@/components/toast-provider'
import { AuthProvider } from '@/components/auth-provider'
import { SessionMonitor } from '@/components/session-monitor'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Orris - ChatGPT for your company docs',
  description: 'An AI chatbot that instantly answers questions about your company documents while automatically protecting sensitive information.',
    generator: 'v0.dev'
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className} suppressHydrationWarning={true}>
        {children}
        <ToastProvider />
      </body>
    </html>
  )
}
