'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { AlertCircle, ChevronRight, FileCheck } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import type { Decision } from '@/lib/types'
import { formatDate } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchDecisions() {
      try {
        setLoading(true)
        setError(null)
        const data = await api.decisions.list({ limit: 50 })
        setDecisions(data)
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message)
        } else {
          setError('Failed to load decisions')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchDecisions()
  }, [])

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading decisions...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Error Loading Decisions
            </CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Decision History</h1>
          <p className="text-muted-foreground mt-2">
            Immutable commitments with complete audit trail
          </p>
        </div>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Decisions</CardDescription>
              <CardTitle className="text-3xl">{decisions.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>With Evidence</CardDescription>
              <CardTitle className="text-3xl">
                {decisions.filter(d => d.evidence_pack_id).length}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Last 7 Days</CardDescription>
              <CardTitle className="text-3xl">
                {decisions.filter(d => {
                  const date = new Date(d.decided_at)
                  const weekAgo = new Date()
                  weekAgo.setDate(weekAgo.getDate() - 7)
                  return date > weekAgo
                }).length}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Decision List */}
        {decisions.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <FileCheck className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No decisions recorded yet</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {decisions.map((decision) => (
              <Link
                key={decision.id}
                href={`/decisions/${decision.id}`}
                className="block"
              >
                <Card className="hover:border-primary transition-colors cursor-pointer">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">
                            {decision.chosen_option_id}
                          </Badge>
                          {decision.evidence_pack_id && (
                            <Badge variant="secondary" className="flex items-center gap-1">
                              <FileCheck className="h-3 w-3" />
                              Evidence Available
                            </Badge>
                          )}
                          <span className="text-xs text-muted-foreground">
                            {formatDate(decision.decided_at)}
                          </span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-muted-foreground mb-1">Rationale:</p>
                          <p className="text-sm line-clamp-2">{decision.rationale}</p>
                        </div>
                        {decision.assumptions && (
                          <div>
                            <p className="text-sm font-medium text-muted-foreground mb-1">Assumptions:</p>
                            <p className="text-sm text-muted-foreground line-clamp-1">{decision.assumptions}</p>
                          </div>
                        )}
                        <p className="text-xs text-muted-foreground">
                          Decided by: {decision.decided_by}
                        </p>
                      </div>
                      <ChevronRight className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-1" />
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
