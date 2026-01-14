'use client'

import { createContext, useContext, useState, ReactNode } from 'react'

export type Pack = 'treasury' | 'wealth'

interface PackContextType {
  pack: Pack
  setPack: (pack: Pack) => void
}

const PackContext = createContext<PackContextType | undefined>(undefined)

export function PackProvider({ children }: { children: ReactNode }) {
  const [pack, setPack] = useState<Pack>('treasury')

  return (
    <PackContext.Provider value={{ pack, setPack }}>
      {children}
    </PackContext.Provider>
  )
}

export function usePack() {
  const context = useContext(PackContext)
  if (context === undefined) {
    throw new Error('usePack must be used within a PackProvider')
  }
  return context
}
