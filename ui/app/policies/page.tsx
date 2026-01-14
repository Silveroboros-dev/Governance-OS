'use client'

import { useEffect, useState } from 'react'
import { AlertCircle, Shield } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import { usePack } from '@/lib/pack-context'
import type { PolicyWithVersion } from '@/lib/types'
import { formatDate } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function PoliciesPage() {
  const { pack } = usePack()
  const [policies, setPolicies] = useState<PolicyWithVersion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchPolicies() {
      try {
        setLoading(true)
        setError(null)
        const data = await api.policies.list({ pack })
        setPolicies(data)
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message)
        } else {
          setError('Failed to load policies')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchPolicies()
  }, [pack])

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading policies...</p>
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
              Error Loading Policies
            </CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  const activePolicies = policies.filter(p => p.active_version?.status === 'active')
  const draftPolicies = policies.filter(p => p.active_version?.status === 'draft')
  const archivedPolicies = policies.filter(p => p.active_version?.status === 'archived')

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Governance Policies</h1>
          <p className="text-muted-foreground mt-2">
            Versioned rules with temporal validity (read-only)
          </p>
        </div>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Active Policies</CardDescription>
              <CardTitle className="text-3xl">{activePolicies.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Draft Policies</CardDescription>
              <CardTitle className="text-3xl">{draftPolicies.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Policies</CardDescription>
              <CardTitle className="text-3xl">{policies.length}</CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Policy List */}
        {policies.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No policies found</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {policies.map((policy) => (
              <Card key={policy.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="flex items-center gap-2">
                        <Shield className="h-5 w-5" />
                        {policy.name}
                      </CardTitle>
                      <CardDescription>{policy.description}</CardDescription>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <Badge variant="outline">{policy.pack}</Badge>
                      {policy.active_version && (
                        <Badge
                          variant={
                            policy.active_version.status === 'active'
                              ? 'default'
                              : policy.active_version.status === 'draft'
                              ? 'secondary'
                              : 'outline'
                          }
                        >
                          {policy.active_version.status}
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                {policy.active_version && (
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground mb-1">Version:</p>
                        <p className="font-medium">v{policy.active_version.version_number}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground mb-1">Valid From:</p>
                        <p className="font-medium">
                          {formatDate(policy.active_version.valid_from)}
                        </p>
                      </div>
                      {policy.active_version.valid_to && (
                        <div>
                          <p className="text-muted-foreground mb-1">Valid To:</p>
                          <p className="font-medium">
                            {formatDate(policy.active_version.valid_to)}
                          </p>
                        </div>
                      )}
                      <div>
                        <p className="text-muted-foreground mb-1">Created By:</p>
                        <p className="font-medium">{policy.created_by}</p>
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground mb-2">Rule Definition:</p>
                      <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto">
                        {JSON.stringify(policy.active_version.rule_definition, null, 2)}
                      </pre>
                    </div>
                  </CardContent>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
