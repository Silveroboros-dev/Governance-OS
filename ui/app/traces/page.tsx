'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { Activity, Clock, CheckCircle, XCircle, AlertCircle, Filter, Bot, ChevronRight } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import type { AgentTrace, AgentType, AgentTraceStatus, TraceStats } from '@/lib/types'
import { formatRelativeTime } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const AGENT_TYPE_LABELS: Record<AgentType, string> = {
  intake: 'Intake Agent',
  narrative: 'Narrative Agent',
  policy_draft: 'Policy Draft Agent',
}

function getStatusColor(status: AgentTraceStatus): string {
  switch (status) {
    case 'running':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    case 'completed':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'failed':
      return 'bg-red-100 text-red-800 border-red-200'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

function getStatusIcon(status: AgentTraceStatus) {
  switch (status) {
    case 'running':
      return <Activity className="h-4 w-4 animate-pulse" />
    case 'completed':
      return <CheckCircle className="h-4 w-4" />
    case 'failed':
      return <XCircle className="h-4 w-4" />
    default:
      return <Clock className="h-4 w-4" />
  }
}

function formatDuration(ms: number | undefined): string {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
}

export default function TracesPage() {
  const [traces, setTraces] = useState<AgentTrace[]>([])
  const [stats, setStats] = useState<TraceStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [agentTypeFilter, setAgentTypeFilter] = useState<AgentType | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<AgentTraceStatus | 'all'>('all')

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const [tracesData, statsData] = await Promise.all([
        api.traces.list({
          agent_type: agentTypeFilter === 'all' ? undefined : agentTypeFilter,
          status: statusFilter === 'all' ? undefined : statusFilter,
          page_size: 50,
        }),
        api.traces.stats(),
      ])

      setTraces(tracesData.items)
      setStats(statsData)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to load traces')
      }
    } finally {
      setLoading(false)
    }
  }, [agentTypeFilter, statusFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading traces...</p>
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
              Error Loading Traces
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
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Activity className="h-8 w-8" />
            Agent Traces
          </h1>
          <p className="text-muted-foreground mt-2">
            Monitor agent executions and tool calls
          </p>
        </div>

        {/* Stats Row */}
        {stats && (
          <div className="grid gap-4 grid-cols-2 md:grid-cols-5">
            <Card
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => setStatusFilter('running')}
            >
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1">
                  <Activity className="h-4 w-4 animate-pulse" />
                  Running
                </CardDescription>
                <CardTitle className="text-2xl text-blue-600">{stats.running}</CardTitle>
              </CardHeader>
            </Card>
            <Card
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => setStatusFilter('completed')}
            >
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1">
                  <CheckCircle className="h-4 w-4" />
                  Completed
                </CardDescription>
                <CardTitle className="text-2xl text-green-600">{stats.completed}</CardTitle>
              </CardHeader>
            </Card>
            <Card
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => setStatusFilter('failed')}
            >
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1">
                  <XCircle className="h-4 w-4" />
                  Failed
                </CardDescription>
                <CardTitle className="text-2xl text-red-600">{stats.failed}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Total</CardDescription>
                <CardTitle className="text-2xl">
                  {stats.running + stats.completed + stats.failed}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Avg Duration</CardDescription>
                <CardTitle className="text-2xl">
                  {formatDuration(stats.average_duration_ms)}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 p-4 bg-muted/50 rounded-lg">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Agent:</span>
            <div className="flex gap-1">
              <Button
                variant={agentTypeFilter === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setAgentTypeFilter('all')}
              >
                All
              </Button>
              {(['intake', 'narrative', 'policy_draft'] as AgentType[]).map(type => (
                <Button
                  key={type}
                  variant={agentTypeFilter === type ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setAgentTypeFilter(type)}
                >
                  {AGENT_TYPE_LABELS[type]}
                </Button>
              ))}
            </div>
          </div>

          <div className="h-6 w-px bg-border" />

          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Status:</span>
            <div className="flex gap-1">
              {(['all', 'running', 'completed', 'failed'] as const).map(status => (
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
        </div>

        {/* Traces List */}
        {traces.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Bot className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No traces match the current filters
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {traces.map((trace) => (
              <Link
                key={trace.id}
                href={`/traces/${trace.id}`}
                className="block"
              >
                <Card className="hover:border-primary transition-colors cursor-pointer">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex-1 space-y-1">
                        {/* Header row */}
                        <div className="flex items-center gap-2 flex-wrap">
                          <Bot className="h-4 w-4 text-muted-foreground" />
                          <Badge variant="outline">
                            {AGENT_TYPE_LABELS[trace.agent_type]}
                          </Badge>
                          <Badge className={getStatusColor(trace.status)}>
                            <span className="flex items-center gap-1">
                              {getStatusIcon(trace.status)}
                              {trace.status}
                            </span>
                          </Badge>
                          {trace.pack && (
                            <Badge variant="secondary">{trace.pack}</Badge>
                          )}
                          <span className="text-xs text-muted-foreground">
                            {formatRelativeTime(trace.started_at)}
                          </span>
                        </div>

                        {/* Details row */}
                        <div className="flex items-center gap-4 text-sm">
                          {trace.document_source && (
                            <span className="text-muted-foreground truncate max-w-xs">
                              Source: {trace.document_source}
                            </span>
                          )}
                          {trace.total_duration_ms && (
                            <span className="text-muted-foreground">
                              Duration: {formatDuration(trace.total_duration_ms)}
                            </span>
                          )}
                        </div>

                        {/* Error message if failed */}
                        {trace.status === 'failed' && trace.error_message && (
                          <p className="text-xs text-red-600 truncate">
                            Error: {trace.error_message}
                          </p>
                        )}

                        {/* Input/output summary */}
                        {trace.input_summary && (
                          <p className="text-xs text-muted-foreground">
                            Input: {JSON.stringify(trace.input_summary).slice(0, 100)}...
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
        )}
      </div>
    </div>
  )
}
