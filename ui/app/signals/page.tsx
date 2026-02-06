'use client'

import { useEffect, useState } from 'react'
import { Activity, Clock, Database, Filter, AlertTriangle, CheckCircle, Eye } from 'lucide-react'
import { api } from '@/lib/api'
import { usePack } from '@/lib/pack-context'
import type { Signal, SignalStats } from '@/lib/types'
import { formatDate } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

function getReliabilityColor(reliability: string): string {
  switch (reliability) {
    case 'verified':
      return 'bg-green-500'
    case 'high':
      return 'bg-blue-500'
    case 'medium':
      return 'bg-yellow-500 text-black'
    case 'low':
      return 'bg-orange-500'
    default:
      return 'bg-gray-500'
  }
}

function getCanonicalStatusBadge(status: string | null | undefined) {
  switch (status) {
    case 'breach':
      return (
        <Badge className="bg-red-500 text-white flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" />
          BREACH
        </Badge>
      )
    case 'observation':
      return (
        <Badge className="bg-amber-500 text-white flex items-center gap-1">
          <Eye className="h-3 w-3" />
          OBSERVATION
        </Badge>
      )
    default:
      return (
        <Badge variant="outline" className="text-muted-foreground">
          Uncategorized
        </Badge>
      )
  }
}

export default function SignalsPage() {
  const { pack } = usePack()
  const [signals, setSignals] = useState<Signal[]>([])
  const [stats, setStats] = useState<SignalStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [signalTypeFilter, setSignalTypeFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  // Get unique signal types for filter
  const signalTypes = Array.from(new Set(signals.map(s => s.signal_type))).sort()

  useEffect(() => {
    async function fetchSignals() {
      try {
        setLoading(true)
        setError(null)
        const [signalsData, statsData] = await Promise.all([
          api.signals.list({ pack, limit: 100 }),
          api.signals.stats(pack)
        ])
        setSignals(signalsData)
        setStats(statsData)
        setSignalTypeFilter('all') // Reset filter when pack changes
        setStatusFilter('all')
      } catch (err) {
        setError('Failed to load signals')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchSignals()
  }, [pack])

  // Filter signals by type and status
  const filteredSignals = signals.filter(s => {
    const matchesType = signalTypeFilter === 'all' || s.signal_type === signalTypeFilter
    const matchesStatus = statusFilter === 'all' ||
      (statusFilter === 'breach' && s.canonical_status === 'breach') ||
      (statusFilter === 'observation' && s.canonical_status === 'observation') ||
      (statusFilter === 'uncategorized' && !s.canonical_status)
    return matchesType && matchesStatus
  })

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading signals...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
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
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Signals</h1>
            <p className="text-muted-foreground mt-2">
              Timestamped facts with provenance ingested by the system
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="flex items-center gap-1">
              <Database className="h-3 w-3" />
              {signals.length} signals
            </Badge>
          </div>
        </div>

        {/* Stats Summary - Key for demo */}
        {stats && (
          <Card className="bg-muted/50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  <span className="font-medium text-foreground">{stats.summary}</span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                    <span className="text-sm"><strong>{stats.breaches}</strong> breaches</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Eye className="h-4 w-4 text-amber-500" />
                    <span className="text-sm"><strong>{stats.observations}</strong> observations</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-gray-400" />
                    <span className="text-sm"><strong>{stats.uncategorized}</strong> uncategorized</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Filters */}
        <Card>
          <CardContent className="pt-6 space-y-4">
            {/* Status Filter */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-2 mr-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Status:</span>
              </div>
              <Button
                variant={statusFilter === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('all')}
              >
                All
              </Button>
              <Button
                variant={statusFilter === 'breach' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('breach')}
                className={statusFilter === 'breach' ? 'bg-red-500 hover:bg-red-600' : ''}
              >
                <AlertTriangle className="h-3 w-3 mr-1" />
                Breaches ({stats?.breaches || 0})
              </Button>
              <Button
                variant={statusFilter === 'observation' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('observation')}
                className={statusFilter === 'observation' ? 'bg-amber-500 hover:bg-amber-600' : ''}
              >
                <Eye className="h-3 w-3 mr-1" />
                Observations ({stats?.observations || 0})
              </Button>
              <Button
                variant={statusFilter === 'uncategorized' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setStatusFilter('uncategorized')}
              >
                Uncategorized ({stats?.uncategorized || 0})
              </Button>
            </div>

            {/* Type Filter */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-2 mr-2">
                <span className="text-sm text-muted-foreground">Type:</span>
              </div>
              <Button
                variant={signalTypeFilter === 'all' ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setSignalTypeFilter('all')}
              >
                All types
              </Button>
              {signalTypes.slice(0, 6).map(type => {
                const count = signals.filter(s => s.signal_type === type).length
                return (
                  <Button
                    key={type}
                    variant={signalTypeFilter === type ? 'secondary' : 'ghost'}
                    size="sm"
                    onClick={() => setSignalTypeFilter(type)}
                  >
                    {type.replace(/_/g, ' ')} ({count})
                  </Button>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* Signals List */}
        {filteredSignals.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Activity className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No signals found</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredSignals.map((signal) => (
              <Card key={signal.id} className="hover:bg-muted/50 transition-colors">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base font-medium">
                        {signal.signal_type.replace(/_/g, ' ')}
                      </CardTitle>
                      <CardDescription className="flex items-center gap-2 mt-1">
                        <span>Source: {signal.source}</span>
                        <span className="text-muted-foreground">|</span>
                        <Clock className="h-3 w-3" />
                        <span>{formatDate(signal.observed_at)}</span>
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      {getCanonicalStatusBadge(signal.canonical_status)}
                      <Badge className={getReliabilityColor(signal.reliability)}>
                        {signal.reliability}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {/* Payload */}
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">Payload</p>
                      <pre className="bg-muted p-3 rounded-lg text-xs overflow-x-auto">
                        {JSON.stringify(signal.payload, null, 2)}
                      </pre>
                    </div>

                    {/* Metadata */}
                    {signal.metadata && Object.keys(signal.metadata).length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-muted-foreground mb-1">Metadata</p>
                        <pre className="bg-muted p-3 rounded-lg text-xs overflow-x-auto">
                          {JSON.stringify(signal.metadata, null, 2)}
                        </pre>
                      </div>
                    )}

                    {/* Footer */}
                    <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t">
                      <span>ID: {signal.id.slice(0, 8)}...</span>
                      <span>Ingested: {formatDate(signal.ingested_at)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
