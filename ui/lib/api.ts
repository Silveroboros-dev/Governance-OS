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

// Combined API object
export const api = {
  exceptions: exceptionApi,
  decisions: decisionApi,
  policies: policyApi,
  signals: signalApi,
  evaluations: evaluationApi,
  evidence: evidenceApi,
}

export { ApiError }
