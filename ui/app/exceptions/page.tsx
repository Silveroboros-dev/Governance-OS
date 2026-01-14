'use client'

import { useEffect, useState, useMemo } from 'react'
import Link from 'next/link'
import { AlertCircle, ChevronRight, Filter, Calendar, Clock } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import { usePack } from '@/lib/pack-context'
import type { Exception, ExceptionStatus, ExceptionSeverity } from '@/lib/types'
import { formatRelativeTime, getSeverityColor, getStatusColor } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

// Group exceptions by date
function groupByDate(exceptions: Exception[]): Map<string, Exception[]> {
  const groups = new Map<string, Exception[]>()

  exceptions.forEach(exc => {
    const date = new Date(exc.raised_at)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    let key: string
    if (date.toDateString() === today.toDateString()) {
      key = 'Today'
    } else if (date.toDateString() === yesterday.toDateString()) {
      key = 'Yesterday'
    } else {
      key = date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
    }

    if (!groups.has(key)) {
      groups.set(key, [])
    }
    groups.get(key)!.push(exc)
  })

  return groups
}

export default function ExceptionsPage() {
  const { pack } = usePack()
  const [exceptions, setExceptions] = useState<Exception[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [statusFilter, setStatusFilter] = useState<ExceptionStatus | 'all'>('open')
  const [severityFilter, setSeverityFilter] = useState<ExceptionSeverity | 'all'>('all')

  useEffect(() => {
    async function fetchExceptions() {
      try {
        setLoading(true)
        setError(null)
        // Fetch all statuses if 'all' selected, otherwise filter
        const status = statusFilter === 'all' ? undefined : statusFilter
        const data = await api.exceptions.list({ status, pack })
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
  }, [statusFilter, pack])

  // Filter by severity client-side
  const filteredExceptions = useMemo(() => {
    if (severityFilter === 'all') return exceptions
    return exceptions.filter(e => e.severity === severityFilter)
  }, [exceptions, severityFilter])

  // Group by date for timeline view
  const groupedExceptions = useMemo(() => {
    return groupByDate(filteredExceptions)
  }, [filteredExceptions])

  // Stats
  const stats = useMemo(() => ({
    total: exceptions.length,
    open: exceptions.filter(e => e.status === 'open').length,
    critical: exceptions.filter(e => e.severity === 'critical').length,
    high: exceptions.filter(e => e.severity === 'high').length,
  }), [exceptions])

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

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Exception Timeline</h1>
          <p className="text-muted-foreground mt-2">
            Interruptions requiring human judgment
          </p>
        </div>

        {/* Stats Row */}
        <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
          <Card className="cursor-pointer hover:border-primary transition-colors" onClick={() => { setStatusFilter('all'); setSeverityFilter('all') }}>
            <CardHeader className="pb-2">
              <CardDescription>Total</CardDescription>
              <CardTitle className="text-2xl">{stats.total}</CardTitle>
            </CardHeader>
          </Card>
          <Card className="cursor-pointer hover:border-primary transition-colors" onClick={() => { setStatusFilter('open'); setSeverityFilter('all') }}>
            <CardHeader className="pb-2">
              <CardDescription>Open</CardDescription>
              <CardTitle className="text-2xl text-amber-600">{stats.open}</CardTitle>
            </CardHeader>
          </Card>
          <Card className="cursor-pointer hover:border-primary transition-colors" onClick={() => setSeverityFilter('critical')}>
            <CardHeader className="pb-2">
              <CardDescription>Critical</CardDescription>
              <CardTitle className="text-2xl text-red-600">{stats.critical}</CardTitle>
            </CardHeader>
          </Card>
          <Card className="cursor-pointer hover:border-primary transition-colors" onClick={() => setSeverityFilter('high')}>
            <CardHeader className="pb-2">
              <CardDescription>High</CardDescription>
              <CardTitle className="text-2xl text-orange-600">{stats.high}</CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 p-4 bg-muted/50 rounded-lg">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Status:</span>
            <div className="flex gap-1">
              {(['all', 'open', 'resolved', 'dismissed'] as const).map(status => (
                <Button
                  key={status}
                  variant={statusFilter === status ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setStatusFilter(status)}
                  className="capitalize"
                >
                  {status}
                </Button>
              ))}
            </div>
          </div>

          <div className="h-6 w-px bg-border" />

          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Severity:</span>
            <div className="flex gap-1">
              {(['all', 'critical', 'high', 'medium', 'low'] as const).map(severity => (
                <Button
                  key={severity}
                  variant={severityFilter === severity ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSeverityFilter(severity)}
                  className={`capitalize ${severity === 'critical' ? 'hover:bg-red-100 dark:hover:bg-red-900' : ''}`}
                >
                  {severity}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Timeline View */}
        {filteredExceptions.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">
                No exceptions match the current filters
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            {Array.from(groupedExceptions.entries()).map(([dateLabel, dateExceptions]) => (
              <div key={dateLabel}>
                {/* Date Header */}
                <div className="flex items-center gap-2 mb-3">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                    {dateLabel}
                  </h2>
                  <Badge variant="outline" className="ml-2">
                    {dateExceptions.length}
                  </Badge>
                </div>

                {/* Exceptions for this date */}
                <div className="space-y-2 ml-6 border-l-2 border-muted pl-4">
                  {dateExceptions.map((exception) => (
                    <Link
                      key={exception.id}
                      href={`/exceptions/${exception.id}`}
                      className="block"
                    >
                      <Card className="hover:border-primary transition-colors cursor-pointer">
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 space-y-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <Badge className={getSeverityColor(exception.severity)}>
                                  {exception.severity}
                                </Badge>
                                <Badge variant="outline" className={getStatusColor(exception.status)}>
                                  {exception.status}
                                </Badge>
                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  {formatRelativeTime(exception.raised_at)}
                                </span>
                              </div>
                              <h3 className="font-medium">{exception.title}</h3>
                              {exception.context?.asset && (
                                <p className="text-xs text-muted-foreground">
                                  Asset: {exception.context.asset}
                                </p>
                              )}
                              {exception.context?.client_id && (
                                <p className="text-xs text-muted-foreground">
                                  Client: {exception.context.client_id}
                                </p>
                              )}
                            </div>
                            <ChevronRight className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                          </div>
                        </CardContent>
                      </Card>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
