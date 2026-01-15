'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  Activity, Clock, CheckCircle, XCircle, AlertCircle,
  ChevronDown, ChevronUp, ArrowLeft, Bot, Wrench
} from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import type { AgentTraceDetail, ToolCall } from '@/lib/types'
import { formatRelativeTime } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const AGENT_TYPE_LABELS: Record<string, string> = {
  intake: 'Intake Agent',
  narrative: 'Narrative Agent',
  policy_draft: 'Policy Draft Agent',
}

function getStatusColor(status: string): string {
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

function getStatusIcon(status: string) {
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

function ToolCallCard({ call, index }: { call: ToolCall; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const hasError = !!call.error

  return (
    <div className={`border rounded-lg p-3 ${hasError ? 'border-red-200 bg-red-50/50' : ''}`}>
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground text-sm w-6">{index + 1}.</span>
          <Wrench className={`h-4 w-4 ${hasError ? 'text-red-500' : 'text-muted-foreground'}`} />
          <span className="font-mono text-sm">{call.tool}</span>
          <span className="text-xs text-muted-foreground">
            {formatDuration(call.duration_ms)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {hasError && <Badge variant="destructive" className="text-xs">Error</Badge>}
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </div>

      {expanded && (
        <div className="mt-3 space-y-3">
          {/* Arguments */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Arguments:</p>
            <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-40">
              {JSON.stringify(call.args, null, 2)}
            </pre>
          </div>

          {/* Result */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">Result:</p>
            <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-40">
              {JSON.stringify(call.result, null, 2)}
            </pre>
          </div>

          {/* Error */}
          {call.error && (
            <div>
              <p className="text-xs font-medium text-red-600 mb-1">Error:</p>
              <pre className="text-xs bg-red-50 text-red-700 p-2 rounded overflow-auto">
                {call.error}
              </pre>
            </div>
          )}

          {/* Timestamp */}
          <p className="text-xs text-muted-foreground">
            Executed: {new Date(call.timestamp).toLocaleString()}
          </p>
        </div>
      )}
    </div>
  )
}

export default function TraceDetailPage() {
  const params = useParams()
  const traceId = params.id as string

  const [trace, setTrace] = useState<AgentTraceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchTrace() {
      try {
        setLoading(true)
        setError(null)
        const data = await api.traces.get(traceId)
        setTrace(data)
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message)
        } else {
          setError('Failed to load trace')
        }
      } finally {
        setLoading(false)
      }
    }

    if (traceId) {
      fetchTrace()
    }
  }, [traceId])

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading trace...</p>
        </div>
      </div>
    )
  }

  if (error || !trace) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Error Loading Trace
            </CardTitle>
            <CardDescription>{error || 'Trace not found'}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        {/* Back link */}
        <Link href="/traces" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back to Traces
        </Link>

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <Bot className="h-6 w-6" />
              {AGENT_TYPE_LABELS[trace.agent_type] || trace.agent_type}
            </h1>
            <p className="text-muted-foreground mt-1 font-mono text-sm">
              Session: {trace.session_id}
            </p>
          </div>
          <Badge className={`${getStatusColor(trace.status)} text-lg px-3 py-1`}>
            <span className="flex items-center gap-1">
              {getStatusIcon(trace.status)}
              {trace.status}
            </span>
          </Badge>
        </div>

        {/* Summary Cards */}
        <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Started</CardDescription>
              <CardTitle className="text-sm">
                {new Date(trace.started_at).toLocaleString()}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Completed</CardDescription>
              <CardTitle className="text-sm">
                {trace.completed_at
                  ? new Date(trace.completed_at).toLocaleString()
                  : '-'
                }
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Duration</CardDescription>
              <CardTitle className="text-xl">
                {formatDuration(trace.total_duration_ms)}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Tool Calls</CardDescription>
              <CardTitle className="text-xl">
                {trace.tool_calls?.length || 0}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Context */}
        {(trace.pack || trace.document_source) && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Context</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {trace.pack && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Pack:</span>
                  <Badge variant="secondary">{trace.pack}</Badge>
                </div>
              )}
              {trace.document_source && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Document Source:</span>
                  <span className="text-sm font-mono">{trace.document_source}</span>
                </div>
              )}
              {trace.approval_count > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Approvals Created:</span>
                  <Badge>{trace.approval_count}</Badge>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Error Message */}
        {trace.status === 'failed' && trace.error_message && (
          <Card className="border-red-200 bg-red-50/50">
            <CardHeader>
              <CardTitle className="text-lg text-red-700 flex items-center gap-2">
                <XCircle className="h-5 w-5" />
                Error
              </CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-sm text-red-700 whitespace-pre-wrap">
                {trace.error_message}
              </pre>
            </CardContent>
          </Card>
        )}

        {/* Input Summary */}
        {trace.input_summary && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Input Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-sm bg-muted p-3 rounded overflow-auto max-h-48">
                {JSON.stringify(trace.input_summary, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}

        {/* Output Summary */}
        {trace.output_summary && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Output Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="text-sm bg-muted p-3 rounded overflow-auto max-h-48">
                {JSON.stringify(trace.output_summary, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}

        {/* Tool Calls Timeline */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Tool Call Timeline
            </CardTitle>
            <CardDescription>
              {trace.tool_calls?.length || 0} tool calls
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!trace.tool_calls || trace.tool_calls.length === 0 ? (
              <p className="text-muted-foreground text-sm">No tool calls recorded</p>
            ) : (
              <div className="space-y-2">
                {trace.tool_calls.map((call, index) => (
                  <ToolCallCard key={index} call={call} index={index} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
