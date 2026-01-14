'use client'

import Link from 'next/link'
import { PackSelector } from '@/components/pack-selector'

export function Header() {
  return (
    <header className="border-b">
      <div className="container mx-auto px-4 py-4">
        <nav className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="text-xl font-bold">
              Governance OS
            </Link>
            <PackSelector />
          </div>
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
  )
}
