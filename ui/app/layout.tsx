import type { Metadata } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { PackProvider } from "@/lib/pack-context"
import { UserProvider } from "@/lib/user-context"
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
          <UserProvider>
            <div className="min-h-screen flex flex-col">
              {/* Demo Mode Banner - No Authentication */}
              <div className="bg-amber-500 text-amber-950 text-center py-1.5 text-sm font-medium">
                DEMO MODE - No Authentication. Reviewer identity is self-reported.
              </div>
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
          </UserProvider>
        </PackProvider>
      </body>
    </html>
  )
}
