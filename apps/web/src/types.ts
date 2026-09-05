export interface User {
  id: string;
  first_name?: string;
  last_name?: string;
  display_name: string;
  email: string;
  roles: string[];
  organization?: string;
  account_status?: string;
  created_at?: string | null;
  last_login_at?: string | null;
}

export interface Session {
  access_token?: string;
  token_type?: "bearer";
  user: User;
  expires_at?: string;
}

export interface Dashboard {
  assigned_claims: number;
  open_reviews: number;
  platform_status: "operational";
  implementation_phase: string;
}

export interface ClaimSummary {
  id: string;
  claim_number: string;
  loss_date: string;
  loss_type: string;
  property_address: string;
  status: string;
  policy_number: string;
  workflow_status: string;
  assigned_to: string | null;
  updated_at: string;
}

export interface Policy {
  id: string;
  policy_number: string;
  product_code: string;
  product_name: string;
  edition: string;
  effective_from: string;
  effective_to: string;
  status: string;
  synthetic_label: string;
}

export interface Document {
  id: string;
  name: string;
  document_type: string;
  content_type: string;
  detected_mime_type: string;
  processing_status: string;
  extraction_status: string;
  page_count: number;
  size_bytes: number;
  checksum_sha256: string;
  uploaded_by: string | null;
  uploaded_at: string;
  injection_risk: boolean;
  synthetic_label: string;
  created_at: string;
}

export interface DocumentPage {
  page_number: number;
  text: string;
  text_sha256: string;
  extraction_method: string;
  extraction_version: string;
  extracted_at: string;
}

export interface DocumentFact {
  id: string;
  page_number: number;
  fact_type: string;
  raw_source_span: string;
  normalized_value: string;
  extraction_method: string;
  extraction_version: string;
}

export interface FactConflict {
  id: string;
  fact_type: string;
  status: string;
  detection_method: string;
  left_document_name: string;
  right_document_name: string;
  left: DocumentFact;
  right: DocumentFact;
}

export interface ProcessingEvent {
  status: string;
  detail: string;
  correlation_id: string;
  created_at: string;
}

export interface DocumentDetail {
  document: Document;
  pages: DocumentPage[];
  facts: DocumentFact[];
  conflicts: FactConflict[];
  processing_history: ProcessingEvent[];
  error_code: string | null;
  error_detail: string | null;
}

export interface FutureSection {
  key: string;
  title: string;
  status: "not_implemented";
  description: string;
}

export interface ClaimWorkspace {
  claim: {
    id: string;
    claim_number: string;
    loss_date: string;
    loss_type: string;
    property_address: string;
    status: string;
    description: string;
    version: number;
  };
  policy: Policy;
  documents: Document[];
  conflicts: FactConflict[];
  workflow: null | {
    id: string;
    workflow_type: string;
    status: string;
    version: string;
    created_at: string;
  };
  human_review_status: string;
  future_sections: FutureSection[];
  synthetic_notice: string;
}

export interface ReviewTask {
  id: string;
  claim_id: string;
  status: string;
  reason_code: string;
  reason: string;
  created_at: string;
  workflow_id: string | null;
  workflow_status: string | null;
  safety_flags: string[];
  claim_number: string | null;
  assigned_to: string | null;
}

export interface OperationsSummary {
  claim_count: number;
  document_count: number;
  workflow_count: number;
  review_count: number;
  ai_metrics_status: "deterministic_model_assistance";
}

export interface Citation {
  id: string;
  claim_id: string;
  document_id: string;
  document_name: string;
  document_type: string;
  page_number: number;
  chunk_identifier: string;
  chunk_ordinal: number;
  source_start: number;
  source_end: number;
  source_checksum: string;
  page_checksum: string;
  excerpt: string;
  policy_edition: string | null;
  applicability_status: string;
  injection_risk: boolean;
  retrieval_rank: number;
  retrieval_score: number;
  lexical_score: number;
  vector_score: number;
  retrieval_method: string;
  source_url: string;
}

export interface GroundedAnswer {
  question: string;
  state:
    | "answerable"
    | "insufficient_evidence"
    | "conflicting_evidence"
    | "ambiguous_evidence";
  answer: string;
  answerable: boolean;
  citations: Citation[];
  retrieved_evidence: Citation[];
  conflicts: Array<{
    fact_type: string;
    left_document_name: string;
    left_value: string;
    right_document_name: string;
    right_value: string;
  }>;
  ambiguity_indicators: string[];
  missing_information: string[];
  human_review_required: boolean;
  applicable_policy_version: string;
  retrieval_configuration: string;
  generator_provider: string;
  generator_model: string;
  generator_version: string;
  retrieval_duration_ms: number;
  embedding_duration_ms: number;
  generation_duration_ms: number;
  correlation_id: string;
}

export interface WorkflowEvent {
  sequence: number;
  event_type: string;
  previous_status: string | null;
  new_status: string;
  stage: string;
  actor_user_id: string | null;
  details: Record<string, unknown>;
  correlation_id: string;
  created_at: string;
}

export interface ControlledWorkflow {
  id: string;
  claim_id: string;
  workflow_type: string;
  workflow_version: string;
  status: string;
  current_stage: string;
  checkpoint_version: number;
  task: string;
  applicable_policy_edition: string;
  human_review_required: boolean;
  approval_state: string;
  retry_count: number;
  max_retries: number;
  correlation_id: string;
  input_fingerprint: string;
  error_code: string | null;
  error_detail: string | null;
  artifact: null | {
    established_evidence: Array<Record<string, unknown>>;
    applicable_policy_evidence: Array<Record<string, unknown>>;
    conflicting_evidence: Array<{
      fact_type: string;
      left_document_name: string;
      left_value: string;
      right_document_name: string;
      right_value: string;
    }>;
    ambiguous_evidence: string[];
    missing_information: string[];
    untrusted_content_flags: string[];
    proposed_next_steps: string[];
    human_review_reason: string | null;
    citations: Citation[];
    authority_notice: string;
    forbidden_actions: string[];
  };
  created_at: string;
  updated_at: string;
}

export interface WorkflowHistory {
  workflow_id: string;
  events: WorkflowEvent[];
}

export interface ClaimEvidenceBrief {
  id: string;
  claim_id: string;
  workflow_id: string | null;
  task: string;
  status:
    | "supported"
    | "insufficient_evidence"
    | "conflicting_evidence"
    | "ambiguous_evidence";
  claim_summary: string;
  evidence_summary: string;
  applicable_policy_summary: string;
  missing_information: string[];
  conflicts: string[];
  ambiguities: string[];
  safety_flags: string[];
  citations: Citation[];
  human_review_required: boolean;
  limitations: string[];
  authority_notice: string;
  stale: boolean;
  validation_state: string;
  evidence_fingerprint: string;
  applicable_policy_edition: string;
  provider: string;
  model_identifier: string;
  configuration_version: string;
  prompt_template_version: string;
  retrieval_configuration: string;
  response_schema_version: string;
  latency_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  retry_count: number;
  correlation_id: string;
  created_at: string;
}
