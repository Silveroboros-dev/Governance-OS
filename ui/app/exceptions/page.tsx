'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { AlertCircle, ChevronRight, Filter } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import type { Exception, ExceptionStatus, ExceptionSeverity } from '@/lib/types'
import { formatRelativeTime, getSeverityColor, getStatusColor } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

export default function ExceptionsPage() {
  const [exceptions, setExceptions] = useState<Exception[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<ExceptionStatus>('open')

  useEffect(() => {
    async function fetchExceptions() {
      try {
        setLoading(true)
        setError(null)
        const data = await api.exceptions.list({ status: statusFilter })
        setExceptions(data)
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message)
        } else {
          setError('Failed to load exceptions')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchExceptions()
  }, [statusFilter])

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading exceptions...</p>
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
              Error Loading Exceptions
            </CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  const openCount = exceptions.filter(e => e.status === 'open').length
  const resolvedCount = exceptions.filter(e => e.status === 'resolved').length

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Exceptions</h1>
          <p className="text-muted-foreground mt-2">
            Interruptions requiring human judgment
          </p>
        </div>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Open</CardDescription>
              <CardTitle className="text-3xl">{openCount}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Resolved</CardDescription>
              <CardTitle className="text-3xl">{resolvedCount}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total</CardDescription>
              <CardTitle className="text-3xl">{exceptions.length}</CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Status:</span>
          <div className="flex gap-2">
            <Button
              variant={statusFilter === 'open' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter('open')}
            >
              Open
            </Button>
            <Button
              variant={statusFilter === 'resolved' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter('resolved')}
            >
              Resolved
            </Button>
            <Button
              variant={statusFilter === 'dismissed' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStatusFilter('dismissed')}
            >
              Dismissed
            </Button>
          </div>
        </div>

        {/* Exception List */}
        {exceptions.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">
                No {statusFilter} exceptions found
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {exceptions.map((exception) => (
              <Link
                key={exception.id}
                href={`/exceptions/${exception.id}`}
                className="block"
              >
                <Card className="hover:border-primary transition-colors cursor-pointer">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge className={getSeverityColor(exception.severity)}>
                            {exception.severity}
                          </Badge>
                          <Badge className={getStatusColor(exception.status)}>
                            {exception.status}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {formatRelativeTime(exception.raised_at)}
                          </span>
                        </div>
                        <h3 className="text-lg font-semibold">{exception.title}</h3>
                        {exception.context?.asset && (
                          <p className="text-sm text-muted-foreground">
                            Asset: {exception.context.asset}
                          </p>
                        )}
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
