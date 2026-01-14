import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { PackProvider } from "@/lib/pack-context"
import { Header } from "@/components/header"

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
        <PackProvider>
          <div className="min-h-screen flex flex-col">
            <Header />
            <main className="flex-1">
              {children}
            </main>
            <footer className="border-t py-4 text-center text-sm text-muted-foreground">
              <div className="container mx-auto px-4">
                Governance OS - Deterministic Governance Kernel
              </div>
            </footer>
          </div>
        </PackProvider>
      </body>
    </html>
  )
}
