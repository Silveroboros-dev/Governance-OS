// TypeScript types mirroring backend Pydantic schemas

// Enums
export type PolicyStatus = "draft" | "active" | "archived"
export type EvaluationResult = "pass" | "fail" | "inconclusive"
export type ExceptionSeverity = "low" | "medium" | "high" | "critical"
export type ExceptionStatus = "open" | "resolved" | "dismissed"
export type SignalReliability = "low" | "medium" | "high" | "verified"

// Policy Types
export interface Policy {
  id: string
  name: string
  pack: string
  description?: string
  created_at: string
  updated_at: string
  created_by: string
}

export interface PolicyVersion {
  id: string
  policy_id: string
  version_number: number
  status: PolicyStatus
  rule_definition: Record<string, any>
  valid_from: string
  valid_to?: string
  changelog?: string
  created_at: string
  created_by: string
}

export interface PolicyWithVersion extends Policy {
  active_version?: PolicyVersion
}

// Signal Types
export interface Signal {
  id: string
  pack: string
  signal_type: string
  payload: Record<string, any>
  source: string
  reliability: SignalReliability
  observed_at: string
  ingested_at: string
  metadata?: Record<string, any>
}

// Evaluation Types
export interface Evaluation {
  id: string
  policy_version_id: string
  signal_ids: string[]
  result: EvaluationResult
  details: Record<string, any>
  input_hash: string
  evaluated_at: string
}

// Exception Types
export interface ExceptionOption {
  id: string
  label: string
  description: string
  implications: string[]
}

export interface Exception {
  id: string
  evaluation_id: string
  fingerprint: string
  severity: ExceptionSeverity
  status: ExceptionStatus
  title: string
  context: Record<string, any>
  options: ExceptionOption[]
  raised_at: string
  resolved_at?: string
}

// Summary types for exception detail (from backend)
export interface EvaluationSummary {
  id: string
  result: string
  details: Record<string, any>
  evaluated_at: string
  input_hash: string
}

export interface PolicySummary {
  id: string
  name: string
  pack: string
  description?: string
  version_number: number
  rule_type?: string
}

export interface SignalSummary {
  id: string
  signal_type: string
  payload: Record<string, any>
  source: string
  reliability: string
  observed_at: string
}

export interface ExceptionDetail extends Exception {
  evaluation?: EvaluationSummary
  policy?: PolicySummary
  signals?: SignalSummary[]
}

// Decision Types
export interface Decision {
  id: string
  exception_id: string
  chosen_option_id: string
  rationale: string
  assumptions?: string
  decided_by: string
  decided_at: string
  evidence_pack_id?: string
}

export interface DecisionDetail extends Decision {
  exception?: Exception
  evidence_pack?: EvidencePack
}

// Evidence Pack Types
export interface EvidencePack {
  id: string
  decision_id: string
  evidence: Record<string, any>
  content_hash: string
  generated_at: string
}

// API Request/Response Types
export interface CreateSignalRequest {
  pack: string
  signal_type: string
  payload: Record<string, any>
  source: string
  reliability: SignalReliability
  observed_at: string
  metadata?: Record<string, any>
}

export interface TriggerEvaluationRequest {
  pack: string
  signal_ids?: string[]
}

export interface CreateDecisionRequest {
  exception_id: string
  chosen_option_id: string
  rationale: string
  assumptions?: string
  decided_by: string
}

// List Response Types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// Query Parameters
export interface ExceptionListParams {
  status?: ExceptionStatus
  severity?: ExceptionSeverity
  pack?: string
  limit?: number
  offset?: number
}

export interface DecisionListParams {
  from_date?: string
  to_date?: string
  decided_by?: string
  pack?: string
  limit?: number
  offset?: number
}

export interface PolicyListParams {
  pack?: string
  status?: PolicyStatus
}

// Stats Types
export interface DashboardStats {
  pack: string
  exceptions: {
    open: number
    by_severity: {
      critical: number
      high: number
      medium: number
      low: number
    }
  }
  decisions: {
    total: number
    last_24h: number
  }
  signals: {
    total: number
    last_24h: number
  }
  policies: {
    total: number
    active: number
  }
}
