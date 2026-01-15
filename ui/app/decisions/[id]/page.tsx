'use client'

import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  AlertCircle,
  Download,
  FileCheck,
  Shield,
  ArrowRight,
  CheckCircle,
  FileText,
  Activity,
  User,
  Clock,
  ChevronRight,
  FileJson,
  FileCode,
  Printer,
  ExternalLink
} from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import type { DecisionDetail, EvidencePack } from '@/lib/types'
import { formatDate, getSeverityColor } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

/**
 * "Why did we do this?" Trace View
 *
 * Shows the accountability chain:
 * Signal(s) → Evaluation → Exception → Decision → Evidence Pack
 *
 * Concise and navigable - no raw data dumps on main view.
 */
export default function DecisionTracePage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [decision, setDecision] = useState<DecisionDetail | null>(null)
  const [evidencePack, setEvidencePack] = useState<EvidencePack | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showRawEvidence, setShowRawEvidence] = useState(false)
  const [showExportMenu, setShowExportMenu] = useState(false)
  const [exporting, setExporting] = useState(false)
  const exportMenuRef = useRef<HTMLDivElement>(null)

  // Close export menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target as Node)) {
        setShowExportMenu(false)
      }
    }
    if (showExportMenu) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showExportMenu])

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        const decisionData = await api.decisions.get(params.id)
        setDecision(decisionData)

        // Always try to fetch evidence pack - it will be generated on demand if not present
        // Note: evidence_pack_id on decision may be null due to immutability constraints,
        // but evidence pack is still accessible via the evidence API
        try {
          const evidenceData = await api.evidence.get(params.id)
          setEvidencePack(evidenceData)
        } catch {
          // Evidence pack not yet available - will show "generating" message
        }
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message)
        } else {
          setError('Failed to load decision')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [params.id])

  const handleExport = async (format: 'json' | 'html' | 'pdf', inline: boolean = false) => {
    try {
      setExporting(true)
      setShowExportMenu(false)

      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

      if (inline && format === 'html') {
        // Open HTML in new tab for viewing/printing
        window.open(`${API_BASE}/evidence/${params.id}/export?format=html&inline=true`, '_blank')
        return
      }

      const blob = await api.evidence.export(params.id, format)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `evidence-${params.id.slice(0, 8)}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      if (err instanceof ApiError && err.status === 501) {
        alert('PDF export is unavailable. Please use HTML export instead.')
      } else {
        alert('Failed to export evidence')
      }
    } finally {
      setExporting(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading trace...</p>
        </div>
      </div>
    )
  }

  if (error || !decision) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Error
            </CardTitle>
            <CardDescription>{error || 'Decision not found'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.back()}>Go Back</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Extract evidence details for display
  const evidence = evidencePack?.evidence || {}
  const signals = evidence.signals || []
  const evaluation = evidence.evaluation || {}
  const policy = evidence.policy || {}

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Decision Trace</p>
            <h1 className="text-2xl font-bold tracking-tight">Why did we do this?</h1>
          </div>
          {evidencePack && (
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="flex items-center gap-1 font-mono text-xs">
                <Shield className="h-3 w-3" />
                {evidencePack.content_hash.slice(0, 12)}...
              </Badge>
              <div className="relative" ref={exportMenuRef}>
                <Button
                  onClick={() => setShowExportMenu(!showExportMenu)}
                  variant="outline"
                  size="sm"
                  disabled={exporting}
                >
                  <Download className="h-4 w-4 mr-2" />
                  {exporting ? 'Exporting...' : 'Export'}
                </Button>
                {showExportMenu && (
                  <div className="absolute right-0 mt-1 w-48 bg-background border rounded-md shadow-lg z-10">
                    <div className="py-1">
                      <button
                        onClick={() => handleExport('html', true)}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted text-left"
                      >
                        <Printer className="h-4 w-4" />
                        <span>View / Print</span>
                        <ExternalLink className="h-3 w-3 ml-auto text-muted-foreground" />
                      </button>
                      <button
                        onClick={() => handleExport('html')}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted text-left"
                      >
                        <FileCode className="h-4 w-4" />
                        <span>Download HTML</span>
                      </button>
                      <button
                        onClick={() => handleExport('json')}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted text-left"
                      >
                        <FileJson className="h-4 w-4" />
                        <span>Download JSON</span>
                      </button>
                      <div className="border-t my-1" />
                      <button
                        onClick={() => handleExport('pdf')}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted text-left text-muted-foreground"
                      >
                        <FileText className="h-4 w-4" />
                        <span>Download PDF</span>
                        <span className="text-xs ml-auto">(optional)</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Trace Flow - Visual Chain */}
        <Card className="bg-muted/30">
          <CardContent className="py-4">
            <div className="flex items-center justify-between gap-2 overflow-x-auto">
              {/* Signals */}
              <div className="flex flex-col items-center min-w-[100px]">
                <div className="w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                  <Activity className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <span className="text-xs font-medium mt-1">Signals</span>
                <span className="text-xs text-muted-foreground">{signals.length} input(s)</span>
              </div>

              <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />

              {/* Evaluation */}
              <div className="flex flex-col items-center min-w-[100px]">
                <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                  <FileText className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <span className="text-xs font-medium mt-1">Evaluation</span>
                <span className="text-xs text-muted-foreground">
                  {evaluation.result === 'fail' ? 'Breach detected' :
                   evaluation.result === 'pass' ? 'Passed' :
                   evaluation.result === 'exception_raised' ? 'Exception' :
                   evaluation.result || 'Checked'}
                </span>
              </div>

              <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />

              {/* Exception */}
              <div className="flex flex-col items-center min-w-[100px]">
                <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900 flex items-center justify-center">
                  <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                </div>
                <span className="text-xs font-medium mt-1">Exception</span>
                <Badge className={`text-xs mt-0.5 ${getSeverityColor(decision.exception?.severity || 'medium')}`}>
                  {decision.exception?.severity || 'unknown'}
                </Badge>
              </div>

              <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />

              {/* Decision */}
              <div className="flex flex-col items-center min-w-[100px]">
                <div className="w-10 h-10 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
                  <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <span className="text-xs font-medium mt-1">Decision</span>
                <span className="text-xs text-muted-foreground">Committed</span>
              </div>

              <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />

              {/* Evidence */}
              <div className="flex flex-col items-center min-w-[100px]">
                <div className="w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                  <FileCheck className="h-5 w-5 text-slate-600 dark:text-slate-400" />
                </div>
                <span className="text-xs font-medium mt-1">Evidence</span>
                <span className="text-xs text-muted-foreground">Sealed</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Decision Summary */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <CardTitle className="text-lg">Decision</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Chosen Option</p>
                <p className="font-medium mt-1">{decision.chosen_option_id.replace(/_/g, ' ')}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Decided By</p>
                <p className="font-medium mt-1 flex items-center gap-1">
                  <User className="h-3 w-3" />
                  {decision.decided_by}
                </p>
              </div>
            </div>
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide">Rationale</p>
              <p className="mt-1 text-sm bg-muted/50 p-3 rounded-lg">{decision.rationale}</p>
            </div>
            {decision.assumptions && (
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wide">Assumptions</p>
                <p className="mt-1 text-sm text-muted-foreground">{decision.assumptions}</p>
              </div>
            )}
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {formatDate(decision.decided_at)}
            </div>
          </CardContent>
        </Card>

        {/* Exception Context */}
        {decision.exception && (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-amber-600" />
                  <CardTitle className="text-lg">Exception</CardTitle>
                </div>
                <Badge className={getSeverityColor(decision.exception.severity)}>
                  {decision.exception.severity}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="font-medium">{decision.exception.title}</p>
              {decision.exception.context && (
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(decision.exception.context).slice(0, 6).map(([key, value]) => (
                    <div key={key} className="flex justify-between">
                      <span className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}:</span>
                      <span className="font-mono text-xs">{String(value)}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Policy */}
        {policy.name && (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-purple-600" />
                <CardTitle className="text-lg">Policy</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{policy.name}</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Version {policy.version_number} · {policy.pack}
                  </p>
                </div>
                <Link href={`/policies`}>
                  <Button variant="ghost" size="sm">
                    View Policy <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Signals */}
        {signals.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-blue-600" />
                <CardTitle className="text-lg">Contributing Signals</CardTitle>
                <Badge variant="outline">{signals.length}</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {signals.slice(0, 5).map((signal: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between p-2 bg-muted/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className="text-xs">
                        {signal.signal_type?.replace(/_/g, ' ')}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        from {signal.source}
                      </span>
                    </div>
                    <Badge variant="secondary" className="text-xs">
                      {signal.reliability}
                    </Badge>
                  </div>
                ))}
                {signals.length > 5 && (
                  <p className="text-xs text-muted-foreground text-center">
                    + {signals.length - 5} more signals
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Evidence Pack - Collapsed by default */}
        {evidencePack && (
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileCheck className="h-5 w-5" />
                  <CardTitle className="text-lg">Evidence Pack</CardTitle>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowRawEvidence(!showRawEvidence)}
                >
                  {showRawEvidence ? 'Hide' : 'Show'} Raw Data
                </Button>
              </div>
              <CardDescription>
                Generated {formatDate(evidencePack.generated_at)} · SHA256: {evidencePack.content_hash.slice(0, 16)}...
              </CardDescription>
            </CardHeader>
            {showRawEvidence && (
              <CardContent>
                <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto max-h-64 overflow-y-auto">
                  {JSON.stringify(evidencePack.evidence, null, 2)}
                </pre>
              </CardContent>
            )}
          </Card>
        )}

        {!evidencePack && (
          <Card>
            <CardContent className="py-8 text-center">
              <AlertCircle className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">
                Evidence pack is being generated...
              </p>
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        <div className="flex justify-between">
          <Button variant="outline" onClick={() => router.push('/decisions')}>
            All Decisions
          </Button>
          <Button variant="outline" onClick={() => router.push('/exceptions')}>
            Back to Exceptions
          </Button>
        </div>
      </div>
    </div>
  )
}
