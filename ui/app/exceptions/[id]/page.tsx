'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle, FileText, CheckCircle } from 'lucide-react'
import { api, ApiError } from '@/lib/api'
import type { ExceptionDetail, ExceptionOption } from '@/lib/types'
import { formatDate, getSeverityColor } from '@/lib/utils'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

export default function ExceptionDecisionPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [exception, setException] = useState<ExceptionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Form state
  const [selectedOption, setSelectedOption] = useState<string>('')
  const [rationale, setRationale] = useState('')
  const [assumptions, setAssumptions] = useState('')

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!selectedOption) {
      alert('Please select an option')
      return
    }

    if (!rationale.trim()) {
      alert('Rationale is required')
      return
    }

    try {
      setSubmitting(true)
      const decision = await api.decisions.create({
        exception_id: params.id,
        chosen_option_id: selectedOption,
        rationale: rationale.trim(),
        assumptions: assumptions.trim() || undefined,
        decided_by: 'user@example.com', // TODO: Get from auth context
      })

      // Redirect to evidence viewer
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

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-screen">
          <p className="text-muted-foreground">Loading exception...</p>
        </div>
      </div>
    )
  }

  if (error || !exception) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Error
            </CardTitle>
            <CardDescription>{error || 'Exception not found'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.back()}>Go Back</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (exception.status !== 'open') {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Exception Already Resolved
            </CardTitle>
            <CardDescription>
              This exception was resolved on {exception.resolved_at && formatDate(exception.resolved_at)}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push('/exceptions')}>View All Exceptions</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="h-screen overflow-hidden flex flex-col">
      {/* Fixed Header */}
      <div className="border-b bg-background">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Decision Required</h1>
              <p className="text-sm text-muted-foreground">Make a commitment with rationale</p>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={getSeverityColor(exception.severity)}>
                {exception.severity}
              </Badge>
              <Dialog>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    <FileText className="h-4 w-4 mr-2" />
                    View Full Evidence
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle>Full Evidence Context</DialogTitle>
                    <DialogDescription>
                      Complete evaluation and signal data
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <h3 className="font-semibold mb-2">Exception Context</h3>
                      <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto">
                        {JSON.stringify(exception.context, null, 2)}
                      </pre>
                    </div>
                    {exception.evaluation && (
                      <div>
                        <h3 className="font-semibold mb-2">Evaluation Details</h3>
                        <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto">
                          {JSON.stringify(exception.evaluation.details, null, 2)}
                        </pre>
                      </div>
                    )}
                    {exception.signals && exception.signals.length > 0 && (
                      <div>
                        <h3 className="font-semibold mb-2">Contributing Signals ({exception.signals.length})</h3>
                        {exception.signals.map((signal, idx) => (
                          <pre key={signal.id} className="bg-muted p-4 rounded-lg text-xs overflow-x-auto mb-2">
                            {JSON.stringify(signal, null, 2)}
                          </pre>
                        ))}
                      </div>
                    )}
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </div>
      </div>

      {/* Scrollable Content Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="container mx-auto px-4 py-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Exception Summary */}
            <Card>
              <CardHeader>
                <CardTitle>{exception.title}</CardTitle>
                <CardDescription>
                  Raised {formatDate(exception.raised_at)}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {exception.context && Object.entries(exception.context).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}:</span>
                    <span className="font-medium">{String(value)}</span>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* SYMMETRIC OPTIONS - NO RANKING, NO RECOMMENDATIONS */}
            <Card>
              <CardHeader>
                <CardTitle>Available Options</CardTitle>
                <CardDescription>
                  All options are presented equally. Select the one that best addresses the situation.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <RadioGroup
                  value={selectedOption}
                  onValueChange={setSelectedOption}
                  className="space-y-4"
                >
                  {exception.options.map((option: ExceptionOption) => (
                    <label
                      key={option.id}
                      className={`flex items-start space-x-3 p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                        selectedOption === option.id
                          ? 'border-primary bg-primary/5'
                          : 'border-border hover:border-muted-foreground/50'
                      }`}
                    >
                      <RadioGroupItem value={option.id} id={option.id} className="mt-1" />
                      <div className="flex-1 space-y-2">
                        <div className="font-semibold">{option.label}</div>
                        <div className="text-sm text-muted-foreground">{option.description}</div>
                        {option.implications && option.implications.length > 0 && (
                          <div className="text-xs space-y-1 mt-2">
                            <div className="font-medium text-muted-foreground">Implications:</div>
                            <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
                              {option.implications.map((implication, idx) => (
                                <li key={idx}>{implication}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </label>
                  ))}
                </RadioGroup>
              </CardContent>
            </Card>

            {/* Rationale (REQUIRED) */}
            <Card>
              <CardHeader>
                <CardTitle>Rationale *</CardTitle>
                <CardDescription>
                  Explain your reasoning for this decision (required)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  placeholder="Why are you choosing this option? What factors influenced your decision?"
                  value={rationale}
                  onChange={(e) => setRationale(e.target.value)}
                  required
                  rows={4}
                  className="resize-none"
                />
              </CardContent>
            </Card>

            {/* Assumptions (OPTIONAL) */}
            <Card>
              <CardHeader>
                <CardTitle>Assumptions</CardTitle>
                <CardDescription>
                  Document any assumptions made (optional)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Textarea
                  placeholder="What assumptions are you making? What uncertainties exist?"
                  value={assumptions}
                  onChange={(e) => setAssumptions(e.target.value)}
                  rows={3}
                  className="resize-none"
                />
              </CardContent>
            </Card>

            {/* Submit */}
            <div className="flex justify-end gap-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.back()}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={submitting || !selectedOption || !rationale.trim()}
              >
                {submitting ? 'Recording Decision...' : 'Commit Decision'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
