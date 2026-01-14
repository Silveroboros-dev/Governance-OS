'use client'

import { useEffect, useState } from 'react'
import Link from "next/link"
import { ArrowRight, AlertTriangle, CheckCircle, FileText, Shield, Activity, Clock } from "lucide-react"
import { api } from '@/lib/api'
import { usePack } from '@/lib/pack-context'
import type { DashboardStats } from '@/lib/types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function Home() {
  const { pack } = usePack()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchStats() {
      try {
        setLoading(true)
        const data = await api.stats.get(pack)
        setStats(data)
      } catch (err) {
        console.error('Failed to fetch stats:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [pack])

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">
            Governance OS
          </h1>
          <p className="text-muted-foreground">
            Policy-driven coordination layer for high-stakes professional work
          </p>
        </div>

        {/* Stats Overview */}
        {loading ? (
          <div className="grid gap-4 md:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i} className="animate-pulse">
                <CardHeader className="pb-2">
                  <div className="h-4 bg-muted rounded w-24" />
                </CardHeader>
                <CardContent>
                  <div className="h-8 bg-muted rounded w-16" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : stats ? (
          <div className="grid gap-4 md:grid-cols-4">
            {/* Open Exceptions */}
            <Card className={stats.exceptions.open > 0 ? 'border-orange-500/50' : ''}>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" />
                  Open Exceptions
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.exceptions.open}</div>
                <div className="flex gap-1 mt-2">
                  {stats.exceptions.by_severity.critical > 0 && (
                    <Badge variant="destructive" className="text-xs">
                      {stats.exceptions.by_severity.critical} critical
                    </Badge>
                  )}
                  {stats.exceptions.by_severity.high > 0 && (
                    <Badge className="bg-orange-500 text-xs">
                      {stats.exceptions.by_severity.high} high
                    </Badge>
                  )}
                  {stats.exceptions.by_severity.medium > 0 && (
                    <Badge className="bg-yellow-500 text-black text-xs">
                      {stats.exceptions.by_severity.medium} med
                    </Badge>
                  )}
                  {stats.exceptions.by_severity.low > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {stats.exceptions.by_severity.low} low
                    </Badge>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Decisions */}
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4" />
                  Decisions Made
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.decisions.total}</div>
                {stats.decisions.last_24h > 0 && (
                  <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {stats.decisions.last_24h} in last 24h
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Signals */}
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  Signals Ingested
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.signals.total}</div>
                {stats.signals.last_24h > 0 && (
                  <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {stats.signals.last_24h} in last 24h
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Policies */}
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-2">
                  <Shield className="h-4 w-4" />
                  Active Policies
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{stats.policies.active}</div>
                <p className="text-xs text-muted-foreground mt-2">
                  of {stats.policies.total} total
                </p>
              </CardContent>
            </Card>
          </div>
        ) : null}

        {/* Navigation Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 pt-4">
          <Link
            href="/exceptions"
            className="group p-6 border rounded-lg hover:border-primary transition-colors"
          >
            <h2 className="text-lg font-semibold mb-2 flex items-center justify-between">
              Exceptions
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </h2>
            <p className="text-sm text-muted-foreground">
              View and resolve exceptions requiring human judgment
            </p>
            {stats && stats.exceptions.open > 0 && (
              <Badge variant="secondary" className="mt-3">
                {stats.exceptions.open} open
              </Badge>
            )}
          </Link>

          <Link
            href="/decisions"
            className="group p-6 border rounded-lg hover:border-primary transition-colors"
          >
            <h2 className="text-lg font-semibold mb-2 flex items-center justify-between">
              Decisions
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </h2>
            <p className="text-sm text-muted-foreground">
              Browse decision history with complete audit trail
            </p>
            {stats && stats.decisions.total > 0 && (
              <Badge variant="secondary" className="mt-3">
                {stats.decisions.total} recorded
              </Badge>
            )}
          </Link>

          <Link
            href="/policies"
            className="group p-6 border rounded-lg hover:border-primary transition-colors"
          >
            <h2 className="text-lg font-semibold mb-2 flex items-center justify-between">
              Policies
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </h2>
            <p className="text-sm text-muted-foreground">
              View active governance policies and rules
            </p>
            {stats && (
              <Badge variant="secondary" className="mt-3">
                {stats.policies.active} active
              </Badge>
            )}
          </Link>

          <Link
            href="/signals"
            className="group p-6 border rounded-lg hover:border-primary transition-colors"
          >
            <h2 className="text-lg font-semibold mb-2 flex items-center justify-between">
              Signals
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </h2>
            <p className="text-sm text-muted-foreground">
              View ingested signals and their payloads
            </p>
            {stats && (
              <Badge variant="secondary" className="mt-3">
                {stats.signals.total} ingested
              </Badge>
            )}
          </Link>
        </div>

        {/* Core Loop */}
        <div className="pt-8 text-center">
          <p className="text-sm text-muted-foreground">
            <strong>Core Loop:</strong> Signal → Policy Evaluation → Exception → Decision → Evidence/Outcome
          </p>
        </div>
      </div>
    </div>
  )
}
