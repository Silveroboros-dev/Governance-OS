import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import Link from "next/link"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Governance OS",
  description: "Policy-driven coordination layer for high-stakes professional work",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen flex flex-col">
          <header className="border-b">
            <div className="container mx-auto px-4 py-4">
              <nav className="flex items-center justify-between">
                <Link href="/" className="text-xl font-bold">
                  Governance OS
                </Link>
                <div className="flex gap-6">
                  <Link href="/exceptions" className="hover:underline">
                    Exceptions
                  </Link>
                  <Link href="/decisions" className="hover:underline">
                    Decisions
                  </Link>
                  <Link href="/policies" className="hover:underline">
                    Policies
                  </Link>
                </div>
              </nav>
            </div>
          </header>
          <main className="flex-1">
            {children}
          </main>
          <footer className="border-t py-4 text-center text-sm text-muted-foreground">
            <div className="container mx-auto px-4">
              Governance OS - Deterministic Governance Kernel
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}
