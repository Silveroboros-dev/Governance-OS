'use client'

import { useState, useEffect } from 'react'
import { User } from 'lucide-react'
import { useUser } from '@/lib/user-context'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

export function UserEmailInput() {
  const { userEmail, setUserEmail } = useUser()
  const [inputValue, setInputValue] = useState('')
  const [open, setOpen] = useState(false)

  useEffect(() => {
    setInputValue(userEmail)
  }, [userEmail])

  const [error, setError] = useState('')

  const handleSave = () => {
    const email = inputValue.trim()
    if (!email || !email.includes('@')) {
      setError('Please enter a valid email address')
      return
    }
    if (email.endsWith('@example.com')) {
      setError('Please enter your real email, not a placeholder')
      return
    }
    setError('')
    setUserEmail(email)
    setOpen(false)
  }

  const displayEmail = userEmail || 'Set Email'

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-2 text-sm">
          <User className="h-4 w-4" />
          <span className="max-w-[150px] truncate">
            {displayEmail}
          </span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>Your Email</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <p className="text-sm text-muted-foreground">
            Used for decision attribution and audit trail
          </p>
          <Input
            placeholder="you@example.com"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSave()
              }
            }}
          />
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <Button onClick={handleSave} className="w-full">
            Save
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
