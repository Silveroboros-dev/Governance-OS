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

// Sprint 3: Approval Queue Types
export type ApprovalActionType = "signal" | "policy_draft" | "decision" | "dismiss" | "context"
export type ApprovalStatus = "pending" | "approved" | "rejected"

export interface Approval {
  id: string
  action_type: ApprovalActionType
  payload: Record<string, any>
  proposed_by: string
  proposed_at: string
  status: ApprovalStatus
  reviewed_by?: string
  reviewed_at?: string
  review_notes?: string
  result_id?: string
  trace_id?: string
  summary?: string
  confidence?: number
}

export interface ApprovalListParams {
  status?: ApprovalStatus
  action_type?: ApprovalActionType
  page?: number
  page_size?: number
}

export interface ApprovalListResponse {
  items: Approval[]
  total: number
  page: number
  page_size: number
}

export interface ApprovalStats {
  pending: number
  approved: number
  rejected: number
  pending_by_type: Record<string, number>
}

// Sprint 3: Agent Trace Types
export type AgentType = "intake" | "narrative" | "policy_draft"
export type AgentTraceStatus = "running" | "completed" | "failed"

export interface ToolCall {
  tool: string
  args: Record<string, any>
  result: any
  duration_ms: number
  timestamp: string
  error?: string
}

export interface AgentTrace {
  id: string
  agent_type: AgentType
  session_id: string
  started_at: string
  completed_at?: string
  status: AgentTraceStatus
  input_summary?: Record<string, any>
  output_summary?: Record<string, any>
  error_message?: string
  total_duration_ms?: number
  pack?: string
  document_source?: string
}

export interface AgentTraceDetail extends AgentTrace {
  tool_calls?: ToolCall[]
  approval_count: number
}

export interface TraceListParams {
  agent_type?: AgentType
  status?: AgentTraceStatus
  pack?: string
  page?: number
  page_size?: number
}

export interface TraceListResponse {
  items: AgentTrace[]
  total: number
  page: number
  page_size: number
}

export interface TraceStats {
  running: number
  completed: number
  failed: number
  by_agent_type: Record<string, number>
  average_duration_ms?: number
}

// Sprint 3: Intake Processing Types
export type Pack = "treasury" | "wealth"

export interface IntakeProcessRequest {
  document_text: string
  pack: Pack
  document_source?: string
}

export interface SourceSpan {
  start_char: number
  end_char: number
  text: string
  page?: number
}

export interface ExtractedSignal {
  signal_type: string
  payload: Record<string, any>
  confidence: number
  source_spans: SourceSpan[]
  extraction_notes?: string
  requires_verification: boolean
}

export interface IntakeProcessResponse {
  trace_id: string
  signals: ExtractedSignal[]
  approval_ids: string[]
  total_candidates: number
  high_confidence: number
  requires_verification: number
  processing_time_ms: number
  extraction_notes?: string
  warnings: string[]
}
