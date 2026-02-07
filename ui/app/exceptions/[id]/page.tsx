'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle, AlertTriangle, Shield, Clock, Info } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import { useUser } from '@/lib/user-context'
import type { ExceptionDetail, ExceptionOption } from '@/lib/types'
import { formatDate, getSeverityColor } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Textarea } from '@/components/ui/textarea'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

/**
 * One-Screen Exception Decision UI
 *
 * Design principles (from CLAUDE.md):
 * - No scrolling, no drilldowns as default path
 * - Options are symmetric (no ranking, no "recommended")
 * - Uncertainty is first-class (confidence gaps visible)
 * - Confirm disabled until rationale entered
 */
export default function ExceptionDecisionPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const { userEmail } = useUser()
  const [exception, setException] = useState<ExceptionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Form state
  const [selectedOption, setSelectedOption] = useState<string>('')
  const [rationale, setRationale] = useState('')

  useEffect(() => {
    async function fetchException() {
      try {
        setLoading(true)
        setError(null)
        const data = await api.exceptions.get(params.id)
        setException(data)
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message)
        } else {
          setError('Failed to load exception')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchException()
  }, [params.id])

  const handleSubmit = async () => {
    if (!selectedOption || !rationale.trim()) return

    if (!userEmail || userEmail.endsWith('@example.com')) {
      alert('Please set your real email in the header before making a decision')
      return
    }

    try {
      setSubmitting(true)
      const decision = await api.decisions.create({
        exception_id: params.id,
        chosen_option_id: selectedOption,
        rationale: rationale.trim(),
        decided_by: userEmail,
      })

      router.push(`/decisions/${decision.id}`)
    } catch (err) {
      if (err instanceof ApiError) {
        alert(`Error: ${err.message}`)
      } else {
        alert('Failed to record decision')
      }
      setSubmitting(false)
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center bg-background" style={{ height: 'calc(100vh - 121px)' }}>
        <p className="text-muted-foreground">Loading...</p>
      </div>
    )
  }

  // Error state
  if (error || !exception) {
    return (
      <div className="flex items-center justify-center bg-background" style={{ height: 'calc(100vh - 121px)' }}>
        <div className="text-center space-y-4">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto" />
          <p className="text-lg font-medium">{error || 'Exception not found'}</p>
          <Button onClick={() => router.back()}>Go Back</Button>
        </div>
      </div>
    )
  }

  // Already resolved
  if (exception.status !== 'open') {
    return (
      <div className="flex items-center justify-center bg-background" style={{ height: 'calc(100vh - 121px)' }}>
        <div className="text-center space-y-4">
          <Shield className="h-12 w-12 text-green-600 mx-auto" />
          <p className="text-lg font-medium">Exception Already Resolved</p>
          <p className="text-sm text-muted-foreground">
            Resolved on {exception.resolved_at && formatDate(exception.resolved_at)}
          </p>
          <Button onClick={() => router.push('/exceptions')}>View All Exceptions</Button>
        </div>
      </div>
    )
  }

  // Extract key facts from signals
  const signalFacts = exception.signals?.map(s => ({
    type: s.signal_type.replace(/_/g, ' '),
    source: s.source,
    reliability: s.reliability,
    ...s.payload
  })) || []

  // Get uncertainty indicators
  const uncertainties: string[] = []
  exception.signals?.forEach(s => {
    if (s.reliability === 'low' || s.reliability === 'unverified') {
      uncertainties.push(`Signal "${s.signal_type}" has ${s.reliability} reliability`)
    }
  })
  if (exception.evaluation?.details?.confidence && exception.evaluation.details.confidence < 0.8) {
    uncertainties.push(`Evaluation confidence: ${(exception.evaluation.details.confidence * 100).toFixed(0)}%`)
  }

  const rationaleMinLength = 10
  const canSubmit = selectedOption && rationale.trim().length >= rationaleMinLength && userEmail

  return (
    <TooltipProvider>
      {/* Use calc to account for global header (~64px) and footer (~57px) */}
      <div className="flex flex-col bg-background overflow-hidden" style={{ height: 'calc(100vh - 121px)' }}>
        {/* Header - Compact */}
        <header className="flex-none border-b px-4 py-2 bg-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Badge className={getSeverityColor(exception.severity)} variant="outline">
                {exception.severity.toUpperCase()}
              </Badge>
              <h1 className="text-base font-semibold truncate max-w-md">{exception.title}</h1>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>{formatDate(exception.raised_at)}</span>
              <Button variant="ghost" size="sm" onClick={() => router.back()}>
                Cancel
              </Button>
            </div>
          </div>
        </header>

        {/* Main Content - Three Column Layout */}
        <main className="flex-1 flex min-h-0 overflow-hidden">
          {/* Left Column: Context */}
          <section className="w-1/3 border-r p-3 flex flex-col min-h-0 overflow-y-auto">
            {/* Policy */}
            {exception.policy && (
              <div className="flex-none mb-3">
                <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                  Impacted Policy
                </h2>
                <div className="bg-muted/50 rounded p-2">
                  <p className="font-medium text-sm">{exception.policy.name}</p>
                  <p className="text-xs text-muted-foreground">
                    v{exception.policy.version_number} · {exception.policy.pack}
                  </p>
                </div>
              </div>
            )}

            {/* What Changed */}
            <div className="flex-none mb-3">
              <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">
                What Changed
              </h2>
              <div className="space-y-1">
                {signalFacts.length > 0 ? (
                  signalFacts.slice(0, 2).map((fact, idx) => (
                    <div key={idx} className="bg-muted/50 rounded p-2 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-medium capitalize text-xs">{fact.type}</span>
                        <Badge variant="outline" className="text-xs py-0">
                          {fact.reliability}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {Object.entries(fact)
                          .filter(([k]) => !['type', 'source', 'reliability'].includes(k))
                          .slice(0, 2)
                          .map(([key, value]) => (
                            <span key={key} className="mr-2">
                              {key.replace(/_/g, ' ')}: <span className="font-mono">{String(value)}</span>
                            </span>
                          ))}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted-foreground">No signal data available</p>
                )}
              </div>
            </div>

            {/* Uncertainty - First Class */}
            {uncertainties.length > 0 && (
              <div className="flex-none">
                <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3 text-amber-500" />
                  Uncertainty
                </h2>
                <div className="bg-amber-500/10 border border-amber-500/20 rounded p-2">
                  <ul className="text-xs text-amber-700 dark:text-amber-400 space-y-0.5">
                    {uncertainties.map((u, idx) => (
                      <li key={idx}>• {u}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </section>

          {/* Center Column: Options */}
          <section className="w-1/3 p-3 flex flex-col min-h-0">
            <h2 className="flex-none text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
              Decision Options
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="h-3 w-3 ml-1 inline cursor-help" />
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-xs max-w-xs">
                    All options are presented equally. There is no recommended choice.
                  </p>
                </TooltipContent>
              </Tooltip>
            </h2>

            <RadioGroup
              value={selectedOption}
              onValueChange={setSelectedOption}
              className="flex-1 overflow-y-auto space-y-1"
            >
              {exception.options.map((option: ExceptionOption) => (
                <label
                  key={option.id}
                  className={`block p-2 border-2 rounded cursor-pointer transition-all ${
                    selectedOption === option.id
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-muted-foreground/50'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <RadioGroupItem value={option.id} id={option.id} className="mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm">{option.label}</div>
                      <div className="text-xs text-muted-foreground">{option.description}</div>
                      {option.implications && option.implications.length > 0 && (
                        <div className="text-xs text-muted-foreground mt-1">
                          {option.implications.slice(0, 2).map((imp, idx) => (
                            <span key={idx} className="mr-1">→ {imp}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </label>
              ))}
            </RadioGroup>
          </section>

          {/* Right Column: Decision Capture */}
          <section className="w-1/3 p-3 flex flex-col min-h-0 bg-muted/30">
            <h2 className="flex-none text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
              Your Decision
            </h2>

            <div className="flex-1 flex flex-col min-h-0">
              {/* Rationale - Required */}
              <div className="flex-1 flex flex-col min-h-0 mb-2">
                <label className="text-xs font-medium mb-1">
                  Rationale <span className="text-destructive">*</span>
                </label>
                <Textarea
                  placeholder="Why are you choosing this option?"
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  className="flex-1 resize-none min-h-[60px] text-sm"
                />
                <p className={`text-xs mt-0.5 ${rationale.length > 0 && rationale.length < rationaleMinLength ? 'text-amber-600' : 'text-muted-foreground'}`}>
                  {rationale.length > 0
                    ? rationale.length < rationaleMinLength
                      ? `${rationale.length}/${rationaleMinLength} chars`
                      : `${rationale.length} chars`
                    : `Min ${rationaleMinLength} chars`}
                </p>
              </div>

              {/* Selected Option Summary */}
              {selectedOption && (
                <div className="flex-none bg-background rounded p-2 mb-2 border">
                  <p className="text-xs text-muted-foreground">Selected:</p>
                  <p className="font-medium text-sm">
                    {exception.options.find(o => o.id === selectedOption)?.label}
                  </p>
                </div>
              )}

              {/* Submit Button */}
              <Button
                onClick={handleSubmit}
                disabled={!canSubmit || submitting}
                className="flex-none w-full"
              >
                {submitting ? 'Recording...' : 'Commit Decision'}
              </Button>

              {!canSubmit && (
                <p className="text-xs text-muted-foreground text-center mt-1">
                  {!userEmail ? 'Set email in header' : !selectedOption ? 'Select option' : rationale.trim().length < rationaleMinLength ? `Enter rationale` : ''}
                </p>
              )}
            </div>
          </section>
        </main>
      </div>
    </TooltipProvider>
  )
}
