from enum import StrEnum


class RoleName(StrEnum):
    CLAIMS_ADJUSTER = "claims_adjuster"
    SUPERVISOR = "supervisor"
    COMPLIANCE_REVIEWER = "compliance_reviewer"
    ADMIN = "admin"


class Action(StrEnum):
    DASHBOARD_READ = "dashboard:read"
    CLAIM_READ = "claim:read"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPLOAD = "document:upload"
    RETRIEVAL_QUERY = "retrieval:query"
    REVIEW_QUEUE_READ = "review_queue:read"
    OPERATIONS_READ = "operations:read"
    SYSTEM_JOB_CREATE = "system_job:create"
    WORKFLOW_START = "workflow:start"
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_REVIEW = "workflow:review"
    WORKFLOW_RETRY = "workflow:retry"
    WORKFLOW_CANCEL = "workflow:cancel"
    BRIEF_CREATE = "brief:create"
    BRIEF_READ = "brief:read"


class WorkflowStatus(StrEnum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    RUNNING = "running"
    HUMAN_REVIEW = "human_review"
    COMPLETED = "completed"
    FAILED = "failed"
    CREATED = "created"
    GATHERING_EVIDENCE = "gathering_evidence"
    EVALUATING_EVIDENCE = "evaluating_evidence"
    DETERMINING_REVIEW_REQUIREMENTS = "determining_review_requirements"
    AWAITING_HUMAN_REVIEW = "awaiting_human_review"
    AWAITING_ADDITIONAL_INFORMATION = "awaiting_additional_information"
    CANCELLED = "cancelled"


class ReviewStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    STORED = "stored"
    EXTRACTING = "extracting"
    CLASSIFYING = "classifying"
    NORMALIZING = "normalizing"
    READY = "ready"
    FAILED = "failed"
    REJECTED = "rejected"
