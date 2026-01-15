'use client'

import { useEffect, useState, useMemo } from 'react'
import { CheckCircle, XCircle, Clock, Filter, Bot, FileText, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import type { Approval, ApprovalStatus, ApprovalActionType, ApprovalStats } from '@/lib/types'
import { formatRelativeTime } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const ACTION_TYPE_LABELS: Record<ApprovalActionType, string> = {
  signal: 'Signal Extraction',
  policy_draft: 'Policy Draft',
  decision: 'Decision Suggestion',
  dismiss: 'Exception Dismissal',
  context: 'Context Addition',
}

const ACTION_TYPE_ICONS: Record<ApprovalActionType, typeof FileText> = {
  signal: FileText,
  policy_draft: FileText,
  decision: CheckCircle,
  dismiss: XCircle,
  context: FileText,
}

function getStatusColor(status: ApprovalStatus): string {
  switch (status) {
    case 'pending':
      return 'bg-amber-100 text-amber-800 border-amber-200'
    case 'approved':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'rejected':
      return 'bg-red-100 text-red-800 border-red-200'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'text-green-600'
  if (confidence >= 0.7) return 'text-amber-600'
  return 'text-red-600'
}

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [stats, setStats] = useState<ApprovalStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [statusFilter, setStatusFilter] = useState<ApprovalStatus | 'all'>('pending')
  const [actionTypeFilter, setActionTypeFilter] = useState<ApprovalActionType | 'all'>('all')

  // Dialog state
  const [selectedApproval, setSelectedApproval] = useState<Approval | null>(null)
  const [dialogType, setDialogType] = useState<'approve' | 'reject' | null>(null)
  const [reviewNotes, setReviewNotes] = useState('')
  const [rejectReason, setRejectReason] = useState('')
  const [reviewerName, setReviewerName] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Expanded payload view
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [approvalsData, statsData] = await Promise.all([
        api.approvals.list({
          status: statusFilter === 'all' ? undefined : statusFilter,
          action_type: actionTypeFilter === 'all' ? undefined : actionTypeFilter,
          page_size: 50,
        }),
        api.approvals.stats(),
      ])

      setApprovals(approvalsData.items)
      setStats(statsData)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to load approvals')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [statusFilter, actionTypeFilter])

  const handleApprove = async () => {
    if (!selectedApproval || !reviewerName.trim()) return

    try {
      setIsSubmitting(true)
      await api.approvals.approve(selectedApproval.id, reviewerName, reviewNotes || undefined)
      setDialogType(null)
      setSelectedApproval(null)
      setReviewNotes('')
      setReviewerName('')
      fetchData()
    } catch (err) {
      if (err instanceof ApiError) {
        alert(`Failed to approve: ${err.message}`)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReject = async () => {
    if (!selectedApproval || !reviewerName.trim()) return

    try {
      setIsSubmitting(true)
      await api.approvals.reject(selectedApproval.id, reviewerName, rejectReason || undefined, reviewNotes || undefined)
      setDialogType(null)
      setSelectedApproval(null)
      setReviewNotes('')
      setRejectReason('')
      setReviewerName('')
      fetchData()
    } catch (err) {
      if (err instanceof ApiError) {
        alert(`Failed to reject: ${err.message}`)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">Loading approvals...</p>
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
              Error Loading Approvals
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
            <Bot className="h-8 w-8" />
            Agent Approval Queue
          </h1>
          <p className="text-muted-foreground mt-2">
            Review and approve agent-proposed actions before they take effect
          </p>
        </div>

        {/* Stats Row */}
        {stats && (
          <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
            <Card
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => setStatusFilter('pending')}
            >
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1">
                  <Clock className="h-4 w-4" />
                  Pending
                </CardDescription>
                <CardTitle className="text-2xl text-amber-600">{stats.pending}</CardTitle>
              </CardHeader>
            </Card>
            <Card
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => setStatusFilter('approved')}
            >
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1">
                  <CheckCircle className="h-4 w-4" />
                  Approved
                </CardDescription>
                <CardTitle className="text-2xl text-green-600">{stats.approved}</CardTitle>
              </CardHeader>
            </Card>
            <Card
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => setStatusFilter('rejected')}
            >
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1">
                  <XCircle className="h-4 w-4" />
                  Rejected
                </CardDescription>
                <CardTitle className="text-2xl text-red-600">{stats.rejected}</CardTitle>
              </CardHeader>
            </Card>
            <Card
              className="cursor-pointer hover:border-primary transition-colors"
              onClick={() => setStatusFilter('all')}
            >
              <CardHeader className="pb-2">
                <CardDescription>Total</CardDescription>
                <CardTitle className="text-2xl">
                  {stats.pending + stats.approved + stats.rejected}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-4 p-4 bg-muted/50 rounded-lg">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Status:</span>
            <div className="flex gap-1">
              {(['all', 'pending', 'approved', 'rejected'] as const).map(status => (
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

          <div className="h-6 w-px bg-border" />

          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Type:</span>
            <div className="flex gap-1 flex-wrap">
              <Button
                variant={actionTypeFilter === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setActionTypeFilter('all')}
              >
                All
              </Button>
              {(['signal', 'policy_draft', 'dismiss', 'context'] as ApprovalActionType[]).map(type => (
                <Button
                  key={type}
                  variant={actionTypeFilter === type ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setActionTypeFilter(type)}
                >
                  {ACTION_TYPE_LABELS[type]}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* Approvals List */}
        {approvals.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Bot className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No approvals match the current filters
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {approvals.map((approval) => {
              const Icon = ACTION_TYPE_ICONS[approval.action_type]
              const isExpanded = expandedId === approval.id

              return (
                <Card key={approval.id} className="hover:border-primary/50 transition-colors">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-2">
                        {/* Header row */}
                        <div className="flex items-center gap-2 flex-wrap">
                          <Icon className="h-4 w-4 text-muted-foreground" />
                          <Badge variant="outline">
                            {ACTION_TYPE_LABELS[approval.action_type]}
                          </Badge>
                          <Badge className={getStatusColor(approval.status)}>
                            {approval.status}
                          </Badge>
                          {approval.confidence !== undefined && approval.confidence !== null && (
                            <span className={`text-xs font-mono ${getConfidenceColor(approval.confidence)}`}>
                              {(approval.confidence * 100).toFixed(0)}% confidence
                            </span>
                          )}
                          <span className="text-xs text-muted-foreground">
                            {formatRelativeTime(approval.proposed_at)}
                          </span>
                        </div>

                        {/* Summary or payload preview */}
                        <div>
                          {approval.summary ? (
                            <p className="font-medium">{approval.summary}</p>
                          ) : (
                            <p className="text-sm text-muted-foreground">
                              Proposed by <span className="font-mono">{approval.proposed_by}</span>
                            </p>
                          )}
                        </div>

                        {/* Payload preview */}
                        {approval.action_type === 'signal' && approval.payload && (
                          <div className="text-sm">
                            <span className="text-muted-foreground">Signal type:</span>{' '}
                            <span className="font-mono">{approval.payload.signal_type}</span>
                            {approval.payload.pack && (
                              <>
                                {' '}| <span className="text-muted-foreground">Pack:</span>{' '}
                                <span className="font-mono">{approval.payload.pack}</span>
                              </>
                            )}
                          </div>
                        )}

                        {/* Expandable payload */}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setExpandedId(isExpanded ? null : approval.id)}
                          className="text-xs"
                        >
                          {isExpanded ? (
                            <>
                              <ChevronUp className="h-3 w-3 mr-1" />
                              Hide Details
                            </>
                          ) : (
                            <>
                              <ChevronDown className="h-3 w-3 mr-1" />
                              Show Details
                            </>
                          )}
                        </Button>

                        {isExpanded && (
                          <pre className="text-xs bg-muted p-3 rounded overflow-auto max-h-64">
                            {JSON.stringify(approval.payload, null, 2)}
                          </pre>
                        )}

                        {/* Review info for processed items */}
                        {approval.status !== 'pending' && approval.reviewed_by && (
                          <div className="text-xs text-muted-foreground pt-2 border-t">
                            {approval.status === 'approved' ? 'Approved' : 'Rejected'} by{' '}
                            <span className="font-medium">{approval.reviewed_by}</span>{' '}
                            {approval.reviewed_at && formatRelativeTime(approval.reviewed_at)}
                            {approval.review_notes && (
                              <p className="mt-1 italic">"{approval.review_notes}"</p>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Action buttons for pending items */}
                      {approval.status === 'pending' && (
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-green-600 hover:bg-green-50 hover:text-green-700"
                            onClick={() => {
                              setSelectedApproval(approval)
                              setDialogType('approve')
                            }}
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Approve
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-red-600 hover:bg-red-50 hover:text-red-700"
                            onClick={() => {
                              setSelectedApproval(approval)
                              setDialogType('reject')
                            }}
                          >
                            <XCircle className="h-4 w-4 mr-1" />
                            Reject
                          </Button>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        )}
      </div>

      {/* Approve Dialog */}
      <Dialog open={dialogType === 'approve'} onOpenChange={(open) => !open && setDialogType(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Approve Action</DialogTitle>
            <DialogDescription>
              This will execute the proposed {selectedApproval && ACTION_TYPE_LABELS[selectedApproval.action_type].toLowerCase()}.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="reviewer">Your Name *</Label>
              <Input
                id="reviewer"
                placeholder="Enter your name"
                value={reviewerName}
                onChange={(e) => setReviewerName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (optional)</Label>
              <Textarea
                id="notes"
                placeholder="Add any notes about this approval..."
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogType(null)}>
              Cancel
            </Button>
            <Button
              onClick={handleApprove}
              disabled={!reviewerName.trim() || isSubmitting}
              className="bg-green-600 hover:bg-green-700"
            >
              {isSubmitting ? 'Approving...' : 'Approve'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject Dialog */}
      <Dialog open={dialogType === 'reject'} onOpenChange={(open) => !open && setDialogType(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject Action</DialogTitle>
            <DialogDescription>
              The proposed {selectedApproval && ACTION_TYPE_LABELS[selectedApproval.action_type].toLowerCase()} will not be executed.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="reviewer-reject">Your Name *</Label>
              <Input
                id="reviewer-reject"
                placeholder="Enter your name"
                value={reviewerName}
                onChange={(e) => setReviewerName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="reason">Rejection Reason</Label>
              <Input
                id="reason"
                placeholder="Brief reason for rejection"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes-reject">Additional Notes (optional)</Label>
              <Textarea
                id="notes-reject"
                placeholder="Add any additional notes..."
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogType(null)}>
              Cancel
            </Button>
            <Button
              onClick={handleReject}
              disabled={!reviewerName.trim() || isSubmitting}
              variant="destructive"
            >
              {isSubmitting ? 'Rejecting...' : 'Reject'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
