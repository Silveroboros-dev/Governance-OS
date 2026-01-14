'use client'

import { useEffect, useState } from 'react'
import { Activity, Clock, Database, Filter } from 'lucide-react'
import { api } from '@/lib/api'
import { usePack } from '@/lib/pack-context'
import type { Signal } from '@/lib/types'
import { formatDate, cn } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

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

export default function SignalsPage() {
  const { pack } = usePack()
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [signalTypeFilter, setSignalTypeFilter] = useState<string>('all')

  // Get unique signal types for filter dropdown
  const signalTypes = [...new Set(signals.map(s => s.signal_type))].sort()

  useEffect(() => {
    async function fetchSignals() {
      try {
        setLoading(true)
        setError(null)
        const data = await api.signals.list({ pack, limit: 100 })
        setSignals(data)
      } catch (err) {
        setError('Failed to load signals')
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    fetchSignals()
  }, [pack])

  // Filter signals by type
  const filteredSignals = signalTypeFilter === 'all'
    ? signals
    : signals.filter(s => s.signal_type === signalTypeFilter)

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

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">Filter by type:</span>
              </div>
              <Select value={signalTypeFilter} onValueChange={setSignalTypeFilter}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All types</SelectItem>
                  {signalTypes.map(type => (
                    <SelectItem key={type} value={type}>
                      {type.replace(/_/g, ' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-sm text-muted-foreground">
                Showing {filteredSignals.length} of {signals.length}
              </span>
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
                    <Badge className={getReliabilityColor(signal.reliability)}>
                      {signal.reliability}
                    </Badge>
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
