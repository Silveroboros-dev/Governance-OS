'use client'

import { useState, useEffect, FormEvent, useCallback } from 'react'
import { Loader2, FileText, CheckCircle, AlertTriangle, ArrowRight, ExternalLink } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { usePack } from '@/lib/pack-context'
import { useUser } from '@/lib/user-context'
import { api, ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { IntakeProcessResponse, ExtractedSignal } from '@/lib/types'

type Status = 'idle' | 'processing' | 'success' | 'error'

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'bg-green-500'
  if (confidence >= 0.7) return 'bg-amber-500'
  return 'bg-red-500'
}

function getConfidenceBorderColor(confidence: number): string {
  if (confidence >= 0.9) return 'border-green-500/50'
  if (confidence >= 0.7) return 'border-amber-500/50'
  return 'border-red-500/50'
}

export default function IngestPage() {
  const { pack } = usePack()
  const { userEmail, setUserEmail } = useUser()
  const [documentText, setDocumentText] = useState('')
  const [documentSource, setDocumentSource] = useState('')
  const [emailInput, setEmailInput] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<IntakeProcessResponse | null>(null)

  // Initialize email input from context
  useEffect(() => {
    if (userEmail && !emailInput) {
      setEmailInput(userEmail)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userEmail])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!emailInput.trim() || !emailInput.includes('@')) {
      setError('Please enter a valid email address')
      return
    }

    if (emailInput.trim().endsWith('@example.com')) {
      setError('Please enter your real email, not a placeholder')
      return
    }

    if (documentText.trim().length < 50) {
      setError('Please enter at least 50 characters')
      return
    }

    // Save email to context for use in decision pages
    setUserEmail(emailInput.trim())

    setStatus('processing')
    setError(null)
    setResult(null)

    try {
      const data = await api.intake.process({
        document_text: documentText,
        pack: pack,
        document_source: documentSource || undefined,
      })

      setResult(data)
      setStatus('success')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('An unexpected error occurred')
      }
      setStatus('error')
    }
  }

  function handleReset() {
    setDocumentText('')
    setDocumentSource('')
    // Keep email - don't reset it
    setStatus('idle')
    setError(null)
    setResult(null)
  }

  const isProcessing = status === 'processing'
  const charCount = documentText.length

  // Warn user if they try to navigate away during processing
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isProcessing) {
        e.preventDefault()
        e.returnValue = 'Document is still being processed. Are you sure you want to leave?'
        return e.returnValue
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [isProcessing])

  return (
    <div className="container mx-auto px-4 py-4">
      <div className="max-w-4xl mx-auto space-y-4">
        {/* Header - Compact */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <FileText className="h-6 w-6" />
              Submit Document
            </h1>
            <p className="text-sm text-muted-foreground">
              Extract signals for <span className="font-medium text-foreground">{pack}</span> pack
            </p>
          </div>
        </div>

        {/* Form Card */}
        <Card>
          <CardContent className="pt-4">
            <form onSubmit={handleSubmit} className="space-y-3">
              {/* Top row: Email + Source side by side */}
              <div className="grid grid-cols-2 gap-4">
                {/* Your Email (required) */}
                <div className="space-y-1">
                  <Label htmlFor="email" className="text-xs">Your Email <span className="text-destructive">*</span></Label>
                  <Input
                    id="email"
                    type="email"
                    value={emailInput}
                    onChange={(e) => setEmailInput(e.target.value)}
                    placeholder="you@company.com"
                    disabled={isProcessing || status === 'success'}
                    maxLength={255}
                    required
                    className="h-9"
                  />
                </div>

                {/* Document Source (optional) */}
                <div className="space-y-1">
                  <Label htmlFor="source" className="text-xs">Document Source (optional)</Label>
                  <Input
                    id="source"
                    value={documentSource}
                    onChange={(e) => setDocumentSource(e.target.value)}
                    placeholder="e.g., Q4 Board Meeting, CFO Email"
                    disabled={isProcessing || status === 'success'}
                    maxLength={500}
                    className="h-9"
                  />
                </div>
              </div>

              {/* Document Textarea - Reduced height */}
              <div className="space-y-1">
                <Label htmlFor="document" className="text-xs">Document Content</Label>
                <Textarea
                  id="document"
                  value={documentText}
                  onChange={(e) => setDocumentText(e.target.value)}
                  placeholder="Paste your document here (memos, reports, correspondence, meeting notes, etc.)..."
                  className={cn(
                    "min-h-[180px] font-mono text-sm resize-y",
                    error && status === 'error' && "border-destructive"
                  )}
                  disabled={isProcessing || status === 'success'}
                  maxLength={50000}
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span className={cn(charCount < 50 && charCount > 0 && "text-amber-600")}>
                    {charCount < 50 ? `${50 - charCount} more chars needed` : 'Ready'}
                  </span>
                  <span>{charCount.toLocaleString()} / 50,000</span>
                </div>
              </div>

              {/* Error Display */}
              {error && status === 'error' && (
                <div className="flex items-center gap-2 rounded bg-destructive/15 p-2 text-destructive">
                  <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                  <p className="text-sm">{error}</p>
                </div>
              )}

              {/* Processing Indicator */}
              {isProcessing && (
                <div className="flex items-center gap-2 p-2 bg-muted rounded">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <span className="text-sm">Analyzing document (10-30s)... <span className="text-muted-foreground">Please do not navigate away.</span></span>
                </div>
              )}

              {/* Submit Button */}
              {status !== 'success' && (
                <Button
                  type="submit"
                  disabled={isProcessing || charCount < 50}
                  className="w-full"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    'Extract Signals'
                  )}
                </Button>
              )}
            </form>
          </CardContent>
        </Card>

        {/* Results Display */}
        {result && (
          <Card className="border-green-500/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-5 w-5" />
                Extraction Complete
              </CardTitle>
              <CardDescription>
                Extracted {result.total_candidates} signal{result.total_candidates !== 1 ? 's' : ''} in{' '}
                {(result.processing_time_ms / 1000).toFixed(1)}s
                {result.high_confidence > 0 && (
                  <> ({result.high_confidence} high confidence)</>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Warnings */}
              {result.warnings.length > 0 && (
                <div className="rounded-md bg-amber-500/15 p-4">
                  <ul className="list-disc list-inside text-sm text-amber-700 dark:text-amber-400 space-y-1">
                    {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                </div>
              )}

              {/* Zero signals case */}
              {result.signals.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="font-medium">No signals could be extracted</p>
                  <p className="text-sm mt-2">
                    Try a document with more specific {pack} content (e.g., position limits, risk thresholds, regulatory filings).
                  </p>
                </div>
              )}

              {/* Extracted Signals */}
              {result.signals.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-sm font-medium text-muted-foreground">
                    Pending Approval ({result.signals.length})
                  </h4>
                  {result.signals.map((signal, index) => (
                    <SignalCard key={index} signal={signal} />
                  ))}
                </div>
              )}

              {/* Navigation Links */}
              <div className="pt-4 border-t space-y-3">
                {result.approval_ids.length > 0 && (
                  <Link href="/approvals">
                    <Button variant="default" className="w-full">
                      Review in Approval Queue
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                  </Link>
                )}

                <Link href={`/traces/${result.trace_id}`}>
                  <Button variant="outline" className="w-full">
                    View Agent Trace
                    <ExternalLink className="ml-2 h-4 w-4" />
                  </Button>
                </Link>

                <Button variant="ghost" className="w-full" onClick={handleReset}>
                  Submit Another Document
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

function SignalCard({ signal }: { signal: ExtractedSignal }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className={cn(
      "rounded-lg border p-4 space-y-3",
      getConfidenceBorderColor(signal.confidence)
    )}>
      <div className="flex items-start justify-between gap-2">
        <h4 className="font-medium capitalize">
          {signal.signal_type.replace(/_/g, ' ')}
        </h4>
        <div className="flex items-center gap-2 flex-shrink-0">
          {signal.requires_verification && (
            <Badge variant="outline" className="text-amber-600 border-amber-600 text-xs">
              Needs Review
            </Badge>
          )}
          <Badge className={cn(getConfidenceColor(signal.confidence), 'text-white text-xs')}>
            {(signal.confidence * 100).toFixed(0)}%
          </Badge>
        </div>
      </div>

      {/* Source Spans */}
      {signal.source_spans.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Source</p>
          <div className="space-y-1">
            {signal.source_spans.slice(0, expanded ? undefined : 2).map((span, i) => (
              <blockquote key={i} className="border-l-2 border-muted-foreground/30 pl-3 text-sm italic text-muted-foreground">
                &ldquo;{span.text.length > 150 && !expanded ? `${span.text.slice(0, 150)}...` : span.text}&rdquo;
              </blockquote>
            ))}
            {signal.source_spans.length > 2 && !expanded && (
              <button
                onClick={() => setExpanded(true)}
                className="text-xs text-primary hover:underline"
              >
                +{signal.source_spans.length - 2} more source{signal.source_spans.length - 2 !== 1 ? 's' : ''}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Extraction Notes */}
      {signal.extraction_notes && (
        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">Agent Notes</p>
          <p className="text-sm text-muted-foreground">{signal.extraction_notes}</p>
        </div>
      )}

      {/* Payload Preview (collapsible) */}
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-primary hover:underline"
        >
          {expanded ? 'Hide' : 'Show'} extracted data
        </button>
        {expanded && (
          <pre className="mt-2 text-xs bg-muted p-3 rounded overflow-auto max-h-48">
            {JSON.stringify(signal.payload, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}
