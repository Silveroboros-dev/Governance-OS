'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface UserContextType {
  userEmail: string
  setUserEmail: (email: string) => void
}

const UserContext = createContext<UserContextType | undefined>(undefined)

const USER_EMAIL_KEY = 'govos_user_email'

export function UserProvider({ children }: { children: ReactNode }) {
  const [userEmail, setUserEmailState] = useState<string>('')

  // Load from localStorage on mount (reject placeholder emails)
  useEffect(() => {
    const stored = localStorage.getItem(USER_EMAIL_KEY)
    if (stored && !stored.endsWith('@example.com')) {
      setUserEmailState(stored)
    } else if (stored?.endsWith('@example.com')) {
      localStorage.removeItem(USER_EMAIL_KEY)
    }
  }, [])

  const setUserEmail = (email: string) => {
    setUserEmailState(email)
    localStorage.setItem(USER_EMAIL_KEY, email)
  }

  return (
    <UserContext.Provider value={{ userEmail, setUserEmail }}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  const context = useContext(UserContext)
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider')
  }
  return context
}
