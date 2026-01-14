'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle, AlertTriangle, Shield, Clock, Info } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
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

    try {
      setSubmitting(true)
      const decision = await api.decisions.create({
        exception_id: params.id,
        chosen_option_id: selectedOption,
        rationale: rationale.trim(),
        decided_by: 'user@example.com', // TODO: Get from auth context
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
      <div className="h-screen flex items-center justify-center bg-background">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    )
  }

  // Error state
  if (error || !exception) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
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
      <div className="h-screen flex items-center justify-center bg-background">
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

  const canSubmit = selectedOption && rationale.trim().length > 0

  return (
    <TooltipProvider>
      <div className="h-screen flex flex-col bg-background overflow-hidden">
        {/* Header - Fixed */}
        <header className="flex-none border-b px-6 py-3 bg-card">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Badge className={getSeverityColor(exception.severity)} variant="outline">
                {exception.severity.toUpperCase()}
              </Badge>
              <h1 className="text-lg font-semibold truncate max-w-xl">{exception.title}</h1>
            </div>
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>{formatDate(exception.raised_at)}</span>
              <Button variant="ghost" size="sm" onClick={() => router.back()}>
                Cancel
              </Button>
            </div>
          </div>
        </header>

        {/* Main Content - Three Column Layout */}
        <main className="flex-1 flex min-h-0">
          {/* Left Column: Context */}
          <section className="w-1/3 border-r p-4 flex flex-col min-h-0">
            {/* Policy */}
            {exception.policy && (
              <div className="flex-none mb-4">
                <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                  Impacted Policy
                </h2>
                <div className="bg-muted/50 rounded-lg p-3">
                  <p className="font-medium">{exception.policy.name}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    v{exception.policy.version_number} · {exception.policy.pack}
                  </p>
                </div>
              </div>
            )}

            {/* What Changed */}
            <div className="flex-none mb-4">
              <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                What Changed
              </h2>
              <div className="space-y-2">
                {signalFacts.length > 0 ? (
                  signalFacts.slice(0, 3).map((fact, idx) => (
                    <div key={idx} className="bg-muted/50 rounded-lg p-3 text-sm">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium capitalize">{fact.type}</span>
                        <Badge variant="outline" className="text-xs">
                          {fact.reliability}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground space-y-0.5">
                        {Object.entries(fact)
                          .filter(([k]) => !['type', 'source', 'reliability'].includes(k))
                          .slice(0, 3)
                          .map(([key, value]) => (
                            <div key={key}>
                              <span className="capitalize">{key.replace(/_/g, ' ')}:</span>{' '}
                              <span className="font-mono">{String(value)}</span>
                            </div>
                          ))}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No signal data available</p>
                )}
              </div>
            </div>

            {/* Uncertainty - First Class */}
            {uncertainties.length > 0 && (
              <div className="flex-none">
                <h2 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3 text-amber-500" />
                  Uncertainty
                </h2>
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
                  <ul className="text-xs text-amber-700 dark:text-amber-400 space-y-1">
                    {uncertainties.map((u, idx) => (
                      <li key={idx}>• {u}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </section>

          {/* Center Column: Options */}
          <section className="w-1/3 p-4 flex flex-col min-h-0">
            <h2 className="flex-none text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
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
              className="flex-1 overflow-y-auto space-y-2 pr-1"
            >
              {exception.options.map((option: ExceptionOption) => (
                <label
                  key={option.id}
                  className={`block p-3 border-2 rounded-lg cursor-pointer transition-all ${
                    selectedOption === option.id
                      ? 'border-primary bg-primary/5 ring-1 ring-primary'
                      : 'border-border hover:border-muted-foreground/50'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <RadioGroupItem value={option.id} id={option.id} className="mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm">{option.label}</div>
                      <div className="text-xs text-muted-foreground mt-1">{option.description}</div>
                      {option.implications && option.implications.length > 0 && (
                        <ul className="mt-2 text-xs text-muted-foreground space-y-0.5">
                          {option.implications.slice(0, 2).map((imp, idx) => (
                            <li key={idx} className="flex items-start gap-1">
                              <span className="text-muted-foreground/50">→</span>
                              <span>{imp}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                </label>
              ))}
            </RadioGroup>
          </section>

          {/* Right Column: Decision Capture */}
          <section className="w-1/3 p-4 flex flex-col min-h-0 bg-muted/30">
            <h2 className="flex-none text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
              Your Decision
            </h2>

            <div className="flex-1 flex flex-col min-h-0">
              {/* Rationale - Required */}
              <div className="flex-1 flex flex-col min-h-0 mb-4">
                <label className="text-sm font-medium mb-2">
                  Rationale <span className="text-destructive">*</span>
                </label>
                <Textarea
                  placeholder="Why are you choosing this option? What factors influenced your decision?"
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  className="flex-1 resize-none min-h-[100px]"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {rationale.length > 0 ? `${rationale.length} characters` : 'Required for audit trail'}
                </p>
              </div>

              {/* Selected Option Summary */}
              {selectedOption && (
                <div className="flex-none bg-background rounded-lg p-3 mb-4 border">
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
                size="lg"
              >
                {submitting ? 'Recording...' : 'Commit Decision'}
              </Button>

              {!canSubmit && (
                <p className="text-xs text-muted-foreground text-center mt-2">
                  {!selectedOption ? 'Select an option' : 'Enter rationale'} to continue
                </p>
              )}
            </div>
          </section>
        </main>
      </div>
    </TooltipProvider>
  )
}
