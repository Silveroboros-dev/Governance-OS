'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle, Download, FileCheck, Shield } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import type { DecisionDetail, EvidencePack } from '@/lib/types'
import { formatDate, getSeverityColor } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

export default function DecisionEvidencePage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [decision, setDecision] = useState<DecisionDetail | null>(null)
  const [evidencePack, setEvidencePack] = useState<EvidencePack | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true)
        setError(null)
        const decisionData = await api.decisions.get(params.id)
        setDecision(decisionData)

        if (decisionData.evidence_pack_id) {
          const evidenceData = await api.evidence.get(params.id)
          setEvidencePack(evidenceData)
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

  const handleExport = async () => {
    try {
      const blob = await api.evidence.export(params.id, 'json')
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `evidence-${params.id}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      alert('Failed to export evidence')
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading evidence...</p>
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

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Decision Evidence</h1>
            <p className="text-muted-foreground mt-2">
              Complete audit-grade evidence pack
            </p>
          </div>
          {evidencePack && (
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="flex items-center gap-1">
                <Shield className="h-3 w-3" />
                Hash: {evidencePack.content_hash.slice(0, 8)}...
              </Badge>
              <Button onClick={handleExport} variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Export JSON
              </Button>
            </div>
          )}
        </div>

        {/* Decision Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Decision</CardTitle>
            <CardDescription>
              Decided {formatDate(decision.decided_at)} by {decision.decided_by}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Chosen Option:</p>
              <Badge variant="default" className="text-base px-3 py-1">
                {decision.chosen_option_id}
              </Badge>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-2">Rationale:</p>
              <p className="text-sm whitespace-pre-wrap">{decision.rationale}</p>
            </div>
            {decision.assumptions && (
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">Assumptions:</p>
                <p className="text-sm whitespace-pre-wrap text-muted-foreground">
                  {decision.assumptions}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Exception Context */}
        {decision.exception && (
          <Card>
            <CardHeader>
              <CardTitle>Exception Context</CardTitle>
              <CardDescription>
                {decision.exception.title}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-2">
                <Badge className={getSeverityColor(decision.exception.severity)}>
                  {decision.exception.severity}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  Raised {formatDate(decision.exception.raised_at)}
                </span>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">Context:</p>
                <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto">
                  {JSON.stringify(decision.exception.context, null, 2)}
                </pre>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Evidence Pack Details */}
        {evidencePack && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileCheck className="h-5 w-5" />
                Evidence Pack
              </CardTitle>
              <CardDescription>
                Generated {formatDate(evidencePack.generated_at)}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">Content Hash (SHA256):</p>
                <code className="text-xs bg-muted px-2 py-1 rounded">
                  {evidencePack.content_hash}
                </code>
              </div>
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">Complete Evidence:</p>
                <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto max-h-96">
                  {JSON.stringify(evidencePack.evidence, null, 2)}
                </pre>
              </div>
            </CardContent>
          </Card>
        )}

        {!evidencePack && (
          <Card>
            <CardContent className="py-8 text-center">
              <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                Evidence pack not yet generated for this decision
              </p>
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        <div className="flex justify-start">
          <Button variant="outline" onClick={() => router.push('/decisions')}>
            Back to Decisions
          </Button>
        </div>
      </div>
    </div>
  )
}
