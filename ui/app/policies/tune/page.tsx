'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  AlertCircle,
  Play,
  GitCompare,
  CheckCircle,
  XCircle,
  ArrowRight,
  Plus,
  Minus,
  Edit3,
  RefreshCw
} from 'lucide-react'
import { usePack } from '@/lib/pack-context'
import { formatDate } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface PolicyVersion {
  id: string
  policy_id: string
  version_number: number
  status: string
  rule_definition: Record<string, any>
  changelog?: string
  created_at: string
  valid_from: string
}

interface Policy {
  id: string
  name: string
  pack: string
  description?: string
  active_version?: PolicyVersion
}

interface ReplayResult {
  replay_id: string
  policy_version_id: string
  policy_name: string
  version_number: number
  is_draft: boolean
  signals_processed: number
  pass_count: number
  fail_count: number
  inconclusive_count: number
  exceptions_raised: number
  executed_at: string
}

interface ComparisonResult {
  baseline_replay_id: string
  comparison_replay_id: string
  baseline_version_number: number
  comparison_version_number: number
  baseline_exceptions: number
  comparison_exceptions: number
  new_exceptions: number
  resolved_exceptions: number
  exception_delta: number
  total_evaluations: number
  matching_evaluations: number
  divergent_evaluations: number
  summary: string
}

export default function PolicyTunePage() {
  const { pack } = usePack()
  const router = useRouter()
  const [policies, setPolicies] = useState<Policy[]>([])
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null)
  const [versions, setVersions] = useState<PolicyVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Replay state
  const [activeReplay, setActiveReplay] = useState<ReplayResult | null>(null)
  const [draftReplay, setDraftReplay] = useState<ReplayResult | null>(null)
  const [comparison, setComparison] = useState<ComparisonResult | null>(null)
  const [replaying, setReplaying] = useState(false)
  const [comparing, setComparing] = useState(false)

  // Load policies
  useEffect(() => {
    async function fetchPolicies() {
      try {
        setLoading(true)
        const res = await fetch(`${API_BASE}/policies?pack=${pack}`)
        if (!res.ok) throw new Error('Failed to load policies')
        const data = await res.json()
        setPolicies(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load policies')
      } finally {
        setLoading(false)
      }
    }
    fetchPolicies()
  }, [pack])

  // Load versions when policy is selected
  useEffect(() => {
    if (!selectedPolicy) {
      setVersions([])
      return
    }

    const policyId = selectedPolicy.id
    async function fetchVersions() {
      try {
        const res = await fetch(`${API_BASE}/policies/${policyId}/versions`)
        if (!res.ok) throw new Error('Failed to load versions')
        const data = await res.json()
        setVersions(data)
      } catch (err) {
        console.error('Failed to load versions:', err)
      }
    }
    fetchVersions()
  }, [selectedPolicy])

  // Run replay for a version
  async function runReplay(versionId: string, isDraft: boolean) {
    try {
      setReplaying(true)
      const res = await fetch(`${API_BASE}/replay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pack,
          policy_version_id: versionId
        })
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Replay failed')
      }
      const result = await res.json()

      if (isDraft) {
        setDraftReplay(result)
      } else {
        setActiveReplay(result)
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Replay failed')
    } finally {
      setReplaying(false)
    }
  }

  // Compare replays
  async function runComparison() {
    if (!activeReplay || !draftReplay) return

    try {
      setComparing(true)
      const res = await fetch(`${API_BASE}/replay/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          baseline_replay_id: activeReplay.replay_id,
          comparison_replay_id: draftReplay.replay_id
        })
      })
      if (!res.ok) throw new Error('Comparison failed')
      const result = await res.json()
      setComparison(result)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Comparison failed')
    } finally {
      setComparing(false)
    }
  }

  const activeVersion = versions.find(v => v.status === 'active')
  const draftVersion = versions.find(v => v.status === 'draft')

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Policy Tuning</h1>
          <p className="text-muted-foreground mt-2">
            Test policy changes before publishing: Draft &rarr; Replay &rarr; Compare &rarr; Publish
          </p>
        </div>

        {/* Workflow Steps */}
        <div className="flex items-center justify-center gap-2 p-4 bg-muted/50 rounded-lg">
          <div className="flex items-center gap-2">
            <Badge variant={selectedPolicy ? "default" : "outline"}>1. Select Policy</Badge>
            <ArrowRight className="h-4 w-4" />
            <Badge variant={draftVersion ? "default" : "outline"}>2. Create Draft</Badge>
            <ArrowRight className="h-4 w-4" />
            <Badge variant={activeReplay && draftReplay ? "default" : "outline"}>3. Run Replay</Badge>
            <ArrowRight className="h-4 w-4" />
            <Badge variant={comparison ? "default" : "outline"}>4. Compare</Badge>
            <ArrowRight className="h-4 w-4" />
            <Badge variant="outline">5. Publish</Badge>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Policy Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Select Policy</CardTitle>
              <CardDescription>Choose a policy to tune</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {policies.map(policy => (
                  <div
                    key={policy.id}
                    className={`p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                      selectedPolicy?.id === policy.id
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:border-muted-foreground/50'
                    }`}
                    onClick={() => {
                      setSelectedPolicy(policy)
                      setActiveReplay(null)
                      setDraftReplay(null)
                      setComparison(null)
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{policy.name}</p>
                        {policy.active_version && (
                          <p className="text-xs text-muted-foreground">
                            v{policy.active_version.version_number} ({policy.active_version.status})
                          </p>
                        )}
                      </div>
                      {policy.active_version && (
                        <Badge variant={policy.active_version.status === 'active' ? 'default' : 'secondary'}>
                          {policy.active_version.status}
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Version Info */}
          <Card>
            <CardHeader>
              <CardTitle>Policy Versions</CardTitle>
              <CardDescription>
                {selectedPolicy ? selectedPolicy.name : 'Select a policy to view versions'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!selectedPolicy ? (
                <p className="text-muted-foreground text-center py-8">
                  Select a policy to begin tuning
                </p>
              ) : (
                <div className="space-y-4">
                  {/* Active Version */}
                  {activeVersion && (
                    <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <CheckCircle className="h-4 w-4 text-green-600" />
                          <span className="font-medium">Active: v{activeVersion.version_number}</span>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => runReplay(activeVersion.id, false)}
                          disabled={replaying}
                        >
                          <Play className="h-3 w-3 mr-1" />
                          Replay
                        </Button>
                      </div>
                      {activeReplay && (
                        <div className="text-xs text-muted-foreground">
                          {activeReplay.signals_processed} signals, {activeReplay.exceptions_raised} exceptions
                        </div>
                      )}
                    </div>
                  )}

                  {/* Draft Version */}
                  {draftVersion ? (
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Edit3 className="h-4 w-4 text-amber-600" />
                          <span className="font-medium">Draft: v{draftVersion.version_number}</span>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => runReplay(draftVersion.id, true)}
                          disabled={replaying}
                        >
                          <Play className="h-3 w-3 mr-1" />
                          Replay
                        </Button>
                      </div>
                      {draftVersion.changelog && (
                        <p className="text-xs text-muted-foreground mb-2">
                          {draftVersion.changelog}
                        </p>
                      )}
                      {draftReplay && (
                        <div className="text-xs text-muted-foreground">
                          {draftReplay.signals_processed} signals, {draftReplay.exceptions_raised} exceptions
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-3 rounded-lg bg-muted/50 border border-dashed">
                      <p className="text-sm text-muted-foreground text-center">
                        No draft version. Create one via API:
                      </p>
                      <pre className="text-xs mt-2 bg-muted p-2 rounded overflow-x-auto">
{`POST /api/v1/policies/${selectedPolicy.id}/versions/draft`}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Comparison Section */}
        {selectedPolicy && activeVersion && draftVersion && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <GitCompare className="h-5 w-5" />
                    Compare Versions
                  </CardTitle>
                  <CardDescription>
                    See the difference between active and draft versions
                  </CardDescription>
                </div>
                <Button
                  onClick={runComparison}
                  disabled={!activeReplay || !draftReplay || comparing}
                >
                  {comparing ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <GitCompare className="h-4 w-4 mr-2" />
                  )}
                  Compare Results
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {!activeReplay || !draftReplay ? (
                <p className="text-muted-foreground text-center py-4">
                  Run replay on both versions to compare results
                </p>
              ) : comparison ? (
                <div className="space-y-4">
                  {/* Summary */}
                  <div className={`p-4 rounded-lg ${
                    comparison.exception_delta > 0
                      ? 'bg-red-500/10 border border-red-500/20'
                      : comparison.exception_delta < 0
                      ? 'bg-green-500/10 border border-green-500/20'
                      : 'bg-blue-500/10 border border-blue-500/20'
                  }`}>
                    <p className="font-medium text-lg">{comparison.summary}</p>
                  </div>

                  {/* Stats Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center p-3 bg-muted/50 rounded-lg">
                      <p className="text-2xl font-bold">{comparison.baseline_exceptions}</p>
                      <p className="text-xs text-muted-foreground">Active Exceptions</p>
                    </div>
                    <div className="text-center p-3 bg-muted/50 rounded-lg">
                      <p className="text-2xl font-bold">{comparison.comparison_exceptions}</p>
                      <p className="text-xs text-muted-foreground">Draft Exceptions</p>
                    </div>
                    <div className="text-center p-3 bg-muted/50 rounded-lg">
                      <p className="text-2xl font-bold text-green-600">-{comparison.resolved_exceptions}</p>
                      <p className="text-xs text-muted-foreground">Resolved</p>
                    </div>
                    <div className="text-center p-3 bg-muted/50 rounded-lg">
                      <p className="text-2xl font-bold text-red-600">+{comparison.new_exceptions}</p>
                      <p className="text-xs text-muted-foreground">New</p>
                    </div>
                  </div>

                  {/* Evaluation Match Rate */}
                  <div className="p-3 bg-muted/50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">Evaluation Match Rate</span>
                      <span className="font-mono">
                        {comparison.matching_evaluations}/{comparison.total_evaluations}
                        ({((comparison.matching_evaluations / comparison.total_evaluations) * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500"
                        style={{
                          width: `${(comparison.matching_evaluations / comparison.total_evaluations) * 100}%`
                        }}
                      />
                    </div>
                    {comparison.divergent_evaluations > 0 && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {comparison.divergent_evaluations} evaluations changed result
                      </p>
                    )}
                  </div>

                  {/* Publish Button */}
                  {comparison.exception_delta <= 0 && (
                    <div className="flex justify-end">
                      <Button
                        onClick={() => {
                          alert('Publish via API: POST /api/v1/policies/{id}/versions/{version_id}/publish')
                        }}
                      >
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Publish Draft (API)
                      </Button>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-4">
                  Click &quot;Compare Results&quot; to see the difference
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Rule Diff (if both versions exist) */}
        {selectedPolicy && activeVersion && draftVersion && (
          <Card>
            <CardHeader>
              <CardTitle>Rule Definition Diff</CardTitle>
              <CardDescription>
                Side-by-side comparison of rule definitions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium mb-2 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    Active (v{activeVersion.version_number})
                  </p>
                  <pre className="bg-muted p-3 rounded-lg text-xs overflow-x-auto max-h-64">
                    {JSON.stringify(activeVersion.rule_definition, null, 2)}
                  </pre>
                </div>
                <div>
                  <p className="text-sm font-medium mb-2 flex items-center gap-2">
                    <Edit3 className="h-4 w-4 text-amber-600" />
                    Draft (v{draftVersion.version_number})
                  </p>
                  <pre className="bg-muted p-3 rounded-lg text-xs overflow-x-auto max-h-64">
                    {JSON.stringify(draftVersion.rule_definition, null, 2)}
                  </pre>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
