// Type-safe API client for Governance OS backend

import type {
  Exception,
  ExceptionDetail,
  ExceptionListParams,
  Decision,
  DecisionDetail,
  DecisionListParams,
  CreateDecisionRequest,
  Policy,
  PolicyWithVersion,
  PolicyListParams,
  Signal,
  CreateSignalRequest,
  Evaluation,
  TriggerEvaluationRequest,
  EvidencePack,
  DashboardStats,
  // Sprint 3 types
  Approval,
  ApprovalListParams,
  ApprovalListResponse,
  ApprovalStats,
  AgentTrace,
  AgentTraceDetail,
  TraceListParams,
  TraceListResponse,
  TraceStats,
  // Intake types
  IntakeProcessRequest,
  IntakeProcessResponse,
} from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

class ApiError extends Error {
  constructor(public status: number, message: string, public data?: any) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(response.status, error.detail || 'API request failed', error)
  }

  return response.json()
}

// Exception API
export const exceptionApi = {
  list: async (params?: ExceptionListParams): Promise<Exception[]> => {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.append('status', params.status)
    if (params?.severity) searchParams.append('severity', params.severity)
    if (params?.pack) searchParams.append('pack', params.pack)
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    if (params?.offset) searchParams.append('offset', params.offset.toString())

    const query = searchParams.toString()
    return fetchApi<Exception[]>(`/exceptions${query ? `?${query}` : ''}`)
  },

  get: async (id: string): Promise<ExceptionDetail> => {
    return fetchApi<ExceptionDetail>(`/exceptions/${id}`)
  },
}

// Decision API
export const decisionApi = {
  list: async (params?: DecisionListParams): Promise<Decision[]> => {
    const searchParams = new URLSearchParams()
    if (params?.from_date) searchParams.append('from_date', params.from_date)
    if (params?.to_date) searchParams.append('to_date', params.to_date)
    if (params?.decided_by) searchParams.append('decided_by', params.decided_by)
    if (params?.pack) searchParams.append('pack', params.pack)
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    if (params?.offset) searchParams.append('offset', params.offset.toString())

    const query = searchParams.toString()
    return fetchApi<Decision[]>(`/decisions${query ? `?${query}` : ''}`)
  },

  get: async (id: string): Promise<DecisionDetail> => {
    return fetchApi<DecisionDetail>(`/decisions/${id}`)
  },

  create: async (data: CreateDecisionRequest): Promise<Decision> => {
    return fetchApi<Decision>('/decisions', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
}

// Policy API
export const policyApi = {
  list: async (params?: PolicyListParams): Promise<PolicyWithVersion[]> => {
    const searchParams = new URLSearchParams()
    if (params?.pack) searchParams.append('pack', params.pack)
    if (params?.status) searchParams.append('status', params.status)

    const query = searchParams.toString()
    return fetchApi<PolicyWithVersion[]>(`/policies${query ? `?${query}` : ''}`)
  },

  get: async (id: string): Promise<PolicyWithVersion> => {
    return fetchApi<PolicyWithVersion>(`/policies/${id}`)
  },
}

// Signal API
export const signalApi = {
  list: async (params?: { pack?: string; signal_type?: string; limit?: number }): Promise<Signal[]> => {
    const searchParams = new URLSearchParams()
    if (params?.pack) searchParams.append('pack', params.pack)
    if (params?.signal_type) searchParams.append('signal_type', params.signal_type)
    if (params?.limit) searchParams.append('limit', params.limit.toString())

    const query = searchParams.toString()
    return fetchApi<Signal[]>(`/signals${query ? `?${query}` : ''}`)
  },

  create: async (data: CreateSignalRequest): Promise<Signal> => {
    return fetchApi<Signal>('/signals', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
}

// Evaluation API
export const evaluationApi = {
  trigger: async (data: TriggerEvaluationRequest): Promise<Evaluation[]> => {
    return fetchApi<Evaluation[]>('/evaluations', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
}

// Evidence API
export const evidenceApi = {
  get: async (decisionId: string): Promise<EvidencePack> => {
    return fetchApi<EvidencePack>(`/evidence/${decisionId}`)
  },

  export: async (decisionId: string, format: string = 'json'): Promise<Blob> => {
    const response = await fetch(
      `${API_BASE_URL}/evidence/${decisionId}/export?format=${format}`
    )
    if (!response.ok) {
      throw new ApiError(response.status, 'Failed to export evidence')
    }
    return response.blob()
  },
}

// Stats API
export const statsApi = {
  get: async (pack?: string): Promise<DashboardStats> => {
    const query = pack ? `?pack=${pack}` : ''
    return fetchApi<DashboardStats>(`/stats${query}`)
  },
}

// Sprint 3: Approval Queue API
export const approvalApi = {
  list: async (params?: ApprovalListParams): Promise<ApprovalListResponse> => {
    const searchParams = new URLSearchParams()
    if (params?.status) searchParams.append('status', params.status)
    if (params?.action_type) searchParams.append('action_type', params.action_type)
    if (params?.page) searchParams.append('page', params.page.toString())
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString())

    const query = searchParams.toString()
    return fetchApi<ApprovalListResponse>(`/approvals${query ? `?${query}` : ''}`)
  },

  get: async (id: string): Promise<Approval> => {
    return fetchApi<Approval>(`/approvals/${id}`)
  },

  approve: async (id: string, reviewedBy: string, notes?: string): Promise<Approval> => {
    return fetchApi<Approval>(`/approvals/${id}/approve?reviewed_by=${encodeURIComponent(reviewedBy)}`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    })
  },

  reject: async (id: string, reviewedBy: string, reason?: string, notes?: string): Promise<Approval> => {
    return fetchApi<Approval>(`/approvals/${id}/reject?reviewed_by=${encodeURIComponent(reviewedBy)}`, {
      method: 'POST',
      body: JSON.stringify({ reason, notes }),
    })
  },

  stats: async (): Promise<ApprovalStats> => {
    return fetchApi<ApprovalStats>('/approvals/stats/summary')
  },
}

// Sprint 3: Agent Traces API
export const traceApi = {
  list: async (params?: TraceListParams): Promise<TraceListResponse> => {
    const searchParams = new URLSearchParams()
    if (params?.agent_type) searchParams.append('agent_type', params.agent_type)
    if (params?.status) searchParams.append('status', params.status)
    if (params?.pack) searchParams.append('pack', params.pack)
    if (params?.page) searchParams.append('page', params.page.toString())
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString())

    const query = searchParams.toString()
    return fetchApi<TraceListResponse>(`/traces${query ? `?${query}` : ''}`)
  },

  get: async (id: string): Promise<AgentTraceDetail> => {
    return fetchApi<AgentTraceDetail>(`/traces/${id}`)
  },

  stats: async (): Promise<TraceStats> => {
    return fetchApi<TraceStats>('/traces/stats/summary')
  },
}

// Sprint 3: Intake Processing API
export const intakeApi = {
  process: async (data: IntakeProcessRequest): Promise<IntakeProcessResponse> => {
    return fetchApi<IntakeProcessResponse>('/intake/process', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
}

// Combined API object
export const api = {
  exceptions: exceptionApi,
  decisions: decisionApi,
  policies: policyApi,
  signals: signalApi,
  evaluations: evaluationApi,
  evidence: evidenceApi,
  stats: statsApi,
  // Sprint 3
  approvals: approvalApi,
  traces: traceApi,
  intake: intakeApi,
}

export { ApiError }
