from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Query, Request, Response, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from insurance_platform.application.schemas import (
    AuthenticatedSessionView,
    CitationView,
    ClaimEvidenceBriefRequest,
    ClaimEvidenceBriefView,
    ClaimSummaryView,
    ClaimWorkspaceView,
    ConflictSummaryView,
    ControlledWorkflowView,
    DashboardView,
    DocumentDetailView,
    DocumentView,
    EvidenceQuery,
    EvidenceSearchView,
    GroundedAnswerView,
    HealthView,
    JobView,
    LoginRequest,
    OperationsSummaryView,
    ReviewTaskView,
    SessionRequest,
    SessionView,
    SmokeJobRequest,
    UserView,
    WorkflowHistoryView,
    WorkflowRetryRequest,
    WorkflowReviewRequest,
    WorkflowStartRequest,
)
from insurance_platform.application.services import PlatformService
from insurance_platform.config import AuthProvider
from insurance_platform.delivery.dependencies import ActorDependency, SessionDependency
from insurance_platform.delivery.errors import (
    DependencyUnavailableError,
    DocumentValidationError,
    RateLimitExceededError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from insurance_platform.documents.ingestion import (
    MAX_DOCUMENT_BYTES,
    DocumentIngestionService,
    DuplicateDocumentError,
    IngestionRejectedError,
)
from insurance_platform.domain.enums import Action
from insurance_platform.infrastructure.models import (
    AuditEventModel,
    OIDCLoginTransactionModel,
    TenantModel,
    UserModel,
    WorkflowRunModel,
)
from insurance_platform.infrastructure.repositories import (
    AuditRepository,
    DocumentRepository,
    UserRepository,
)
from insurance_platform.model_assistance.service import (
    BriefConflictError,
    BriefGenerationError,
    BriefNotFoundError,
    ClaimEvidenceBriefService,
)
from insurance_platform.observability.metrics import (
    AUTH_ATTEMPTS,
    RATE_LIMIT_REJECTIONS,
)
from insurance_platform.ports.identity import IdentityError
from insurance_platform.ports.queue import Job
from insurance_platform.retrieval.embeddings import DeterministicHashEmbeddingProvider
from insurance_platform.retrieval.search import FUSION_VERSION, RetrievedEvidence
from insurance_platform.retrieval.service import (
    GroundedAnswerService,
    RetrievalService,
    stable_citation_id,
)
from insurance_platform.security.authorization import authorize
from insurance_platform.security.local_identity import LocalIdentityProvider
from insurance_platform.security.oidc import login_material, opaque_hash
from insurance_platform.security.sessions import LocalAccountSessionService
from insurance_platform.workflows.service import (
    ControlledWorkflowService,
    WorkflowConflictError,
    WorkflowExecutionError,
    WorkflowNotFoundError,
)


def build_system_router() -> APIRouter:
    router = APIRouter(tags=["system"])

    @router.get("/health/live", response_model=HealthView)
    async def live(request: Request) -> HealthView:
        settings = request.app.state.components.settings
        return HealthView(
            status="ok", version=settings.app_version, environment=settings.app_env.value
        )

    @router.get("/health/ready", response_model=HealthView)
    async def ready(request: Request, response: Response) -> HealthView:
        components = request.app.state.components
        checks: dict[str, str] = {}
        readiness_status = "ready"
        try:
            with components.engine.connect() as connection:
                connection.execute(select(1))
            checks["database"] = "ready"
        except Exception:
            checks["database"] = "unavailable"
            readiness_status = "not_ready"
        try:
            object_storage_ready = await components.object_storage.healthcheck()
        except Exception:
            object_storage_ready = False
        checks["object_storage"] = "ready" if object_storage_ready else "unavailable"
        try:
            queue_ready = await components.job_queue.healthcheck()
        except Exception:
            queue_ready = False
        checks["queue"] = "ready" if queue_ready else "unavailable"
        if "unavailable" in checks.values():
            readiness_status = "not_ready"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthView(
            status=readiness_status,
            version=components.settings.app_version,
            environment=components.settings.app_env.value,
            checks=checks,
        )

    return router


def build_api_router() -> APIRouter:
    router = APIRouter()
    auth = APIRouter(prefix="/auth", tags=["authentication"])

    def enforce_limit(request: Request, *, scope: str, subject: str, limit: int) -> None:
        settings = request.app.state.components.settings
        try:
            decision = request.app.state.components.rate_limiter.check(
                scope=scope,
                subject=hashlib.sha256(subject.encode()).hexdigest(),
                limit=limit,
                window_seconds=settings.rate_limit_window_seconds,
            )
        except Exception as exc:
            raise DependencyUnavailableError(
                "The abuse-protection service is temporarily unavailable."
            ) from exc
        if not decision.allowed:
            RATE_LIMIT_REJECTIONS.labels(scope=scope).inc()
            raise RateLimitExceededError(decision.retry_after_seconds)

    def user_view(session: SessionDependency, user: UserModel) -> UserView:
        tenant = session.get(TenantModel, user.tenant_id)
        return UserView(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            display_name=user.display_name,
            email=user.email,
            roles=sorted(role.name for role in user.roles),
            organization=tenant.name if tenant else "",
            account_status=user.account_status,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )

    @auth.post("/login", response_model=AuthenticatedSessionView)
    def login(
        payload: LoginRequest,
        request: Request,
        response: Response,
        session: SessionDependency,
    ) -> AuthenticatedSessionView:
        components = request.app.state.components
        if components.settings.auth_provider is not AuthProvider.LOCAL:
            raise ResourceNotFoundError("local account sign-in is disabled")
        client = request.client.host if request.client else "unknown"
        enforce_limit(
            request,
            scope="authentication",
            subject=f"{client}:{payload.email.strip().lower()}",
            limit=components.settings.auth_rate_limit,
        )
        try:
            issued = LocalAccountSessionService(
                session,
                ttl_seconds=components.settings.session_ttl_seconds,
                remember_ttl_seconds=components.settings.session_remember_ttl_seconds,
            ).authenticate(payload.email, payload.password, remember=payload.remember)
        except IdentityError:
            AUTH_ATTEMPTS.labels(provider="local", outcome="failure").inc()
            raise
        AUTH_ATTEMPTS.labels(provider="local", outcome="success").inc()
        max_age = int(issued.expires_at.timestamp() - time.time())
        response.set_cookie(
            key=components.settings.session_cookie_name,
            value=issued.token,
            max_age=max_age,
            expires=issued.expires_at,
            path="/",
            secure=components.settings.app_env not in {"local", "test"},
            httponly=True,
            samesite="lax",
        )
        response.headers["Cache-Control"] = "no-store"
        AuditRepository(session).append(
            AuditEventModel(
                tenant_id=issued.user.tenant_id,
                actor_user_id=issued.user.id,
                action="authentication.login",
                resource_type="session",
                resource_id="self",
                outcome="success",
                correlation_id=request.state.correlation_id,
                details={"provider": "local", "remember": payload.remember},
            )
        )
        return AuthenticatedSessionView(
            user=user_view(session, issued.user), expires_at=issued.expires_at
        )

    @auth.get("/session", response_model=UserView)
    def current_session(actor: ActorDependency, session: SessionDependency) -> UserView:
        user = UserRepository(session).get(actor.user_id, actor.tenant_id)
        if user is None:
            raise ResourceNotFoundError("user not found")
        return user_view(session, user)

    @auth.get("/oidc/start", response_class=RedirectResponse)
    def oidc_start(request: Request, session: SessionDependency) -> RedirectResponse:
        components = request.app.state.components
        settings = components.settings
        if settings.auth_provider is not AuthProvider.OIDC or components.oidc_client is None:
            raise ResourceNotFoundError("enterprise sign-in is not configured")
        client_host = request.client.host if request.client else "unknown"
        enforce_limit(
            request,
            scope="authentication",
            subject=f"oidc:{client_host}",
            limit=settings.auth_rate_limit,
        )
        material = login_material()
        assert settings.oidc_redirect_uri is not None
        session.add(
            OIDCLoginTransactionModel(
                state_hash=opaque_hash(material.state),
                nonce_hash=opaque_hash(material.nonce),
                browser_binding_hash=opaque_hash(material.browser_binding),
                code_verifier=material.code_verifier,
                redirect_uri=settings.oidc_redirect_uri,
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
            )
        )
        session.commit()
        destination = components.oidc_client.authorization_url(
            state=material.state,
            nonce=material.nonce,
            code_challenge=material.code_challenge,
            redirect_uri=settings.oidc_redirect_uri,
        )
        response = RedirectResponse(destination, status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key=f"{settings.session_cookie_name}_oidc",
            value=material.browser_binding,
            max_age=600,
            path="/api/v1/auth/oidc/callback",
            secure=settings.app_env not in {"local", "test"},
            httponly=True,
            samesite="lax",
        )
        return response

    @auth.get("/oidc/callback", response_class=RedirectResponse)
    def oidc_callback(
        request: Request,
        session: SessionDependency,
        code: Annotated[str, Query(min_length=1, max_length=4096)],
        state_value: Annotated[str, Query(alias="state", min_length=16, max_length=512)],
    ) -> RedirectResponse:
        components = request.app.state.components
        settings = components.settings
        if settings.auth_provider is not AuthProvider.OIDC or components.oidc_client is None:
            raise ResourceNotFoundError("enterprise sign-in is not configured")
        transaction = session.scalar(
            select(OIDCLoginTransactionModel).where(
                OIDCLoginTransactionModel.state_hash == opaque_hash(state_value),
                OIDCLoginTransactionModel.consumed_at.is_(None),
            )
        )
        now = datetime.now(UTC)
        binding = request.cookies.get(f"{settings.session_cookie_name}_oidc", "")
        if transaction is None or not binding:
            raise IdentityError("OIDC login transaction is invalid or expired")
        expires_at = (
            transaction.expires_at
            if transaction.expires_at.tzinfo
            else transaction.expires_at.replace(tzinfo=UTC)
        )
        if expires_at <= now or not hmac.compare_digest(
            transaction.browser_binding_hash, opaque_hash(binding)
        ):
            raise IdentityError("OIDC login transaction is invalid or expired")
        transaction.consumed_at = now
        session.commit()
        external = components.oidc_client.exchange(
            code=code,
            code_verifier=transaction.code_verifier,
            redirect_uri=transaction.redirect_uri,
            expected_nonce_hash=transaction.nonce_hash,
        )
        assert settings.oidc_tenant_id is not None
        user = UserRepository(session).get_by_subject(external.subject, settings.oidc_tenant_id)
        if user is None:
            AUTH_ATTEMPTS.labels(provider="oidc", outcome="unmapped").inc()
            raise IdentityError("OIDC identity does not map to an active application user")
        issued = LocalAccountSessionService(
            session,
            ttl_seconds=settings.session_ttl_seconds,
            remember_ttl_seconds=settings.session_remember_ttl_seconds,
        ).issue_for_user(user, remember=False)
        AUTH_ATTEMPTS.labels(provider="oidc", outcome="success").inc()
        AuditRepository(session).append(
            AuditEventModel(
                tenant_id=user.tenant_id,
                actor_user_id=user.id,
                action="authentication.login",
                resource_type="session",
                resource_id="self",
                outcome="success",
                correlation_id=request.state.correlation_id,
                details={"provider": "oidc"},
            )
        )
        response = RedirectResponse(settings.public_base_url, status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key=settings.session_cookie_name,
            value=issued.token,
            max_age=int(issued.expires_at.timestamp() - time.time()),
            expires=issued.expires_at,
            path="/",
            secure=settings.app_env not in {"local", "test"},
            httponly=True,
            samesite="lax",
        )
        response.delete_cookie(
            f"{settings.session_cookie_name}_oidc", path="/api/v1/auth/oidc/callback"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @auth.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(request: Request, response: Response, session: SessionDependency) -> None:
        settings = request.app.state.components.settings
        token = request.cookies.get(settings.session_cookie_name)
        if token:
            LocalAccountSessionService(
                session,
                ttl_seconds=settings.session_ttl_seconds,
                remember_ttl_seconds=settings.session_remember_ttl_seconds,
            ).revoke(token)
        response.delete_cookie(settings.session_cookie_name, path="/")

    @auth.get("/dev/users", response_model=list[UserView])
    def dev_users(request: Request, session: SessionDependency) -> list[UserView]:
        if request.app.state.components.settings.auth_provider is not AuthProvider.LOCAL:
            raise ResourceNotFoundError("local identity endpoints are disabled")
        return PlatformService(session).list_dev_users()

    @auth.post("/dev/session", response_model=SessionView)
    def dev_session(
        payload: SessionRequest, request: Request, session: SessionDependency
    ) -> SessionView:
        components = request.app.state.components
        if components.settings.auth_provider is not AuthProvider.LOCAL:
            raise ResourceNotFoundError("local identity endpoints are disabled")
        user = UserRepository(session).get_active(payload.user_id)
        if user is None:
            raise ResourceNotFoundError("development user not found")
        provider = components.identity_provider
        if not isinstance(provider, LocalIdentityProvider):
            raise ResourceNotFoundError("local identity provider is disabled")
        token = provider.issue(user.id, user.tenant_id, user.subject)
        return SessionView(
            access_token=token,
            user=UserView(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                display_name=user.display_name,
                email=user.email,
                roles=sorted(role.name for role in user.roles),
            ),
        )

    router.include_router(auth)

    @router.get("/me", response_model=UserView, tags=["identity"])
    def me(actor: ActorDependency, session: SessionDependency) -> UserView:
        user = UserRepository(session).get(actor.user_id, actor.tenant_id)
        if user is None:
            raise ResourceNotFoundError("user not found")
        return user_view(session, user)

    @router.get("/dashboard", response_model=DashboardView, tags=["dashboard"])
    def dashboard(actor: ActorDependency, session: SessionDependency) -> DashboardView:
        authorize(actor, Action.DASHBOARD_READ)
        return PlatformService(session).dashboard(actor)

    @router.get("/claims", response_model=list[ClaimSummaryView], tags=["claims"])
    def claims(
        actor: ActorDependency,
        session: SessionDependency,
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
        offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    ) -> list[ClaimSummaryView]:
        authorize(actor, Action.CLAIM_READ)
        return PlatformService(session).list_claims(actor, limit=limit, offset=offset)

    @router.get("/claims/{claim_id}", response_model=ClaimWorkspaceView, tags=["claims"])
    def claim_workspace(
        claim_id: UUID, request: Request, actor: ActorDependency, session: SessionDependency
    ) -> ClaimWorkspaceView:
        authorize(actor, Action.CLAIM_READ)
        workspace = PlatformService(session).claim_workspace(claim_id, actor)
        if workspace is None:
            raise ResourceNotFoundError("claim not found")
        AuditRepository(session).append(
            AuditEventModel(
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                action="claim.workspace.read",
                resource_type="claim",
                resource_id=str(claim_id),
                outcome="success",
                correlation_id=request.state.correlation_id,
                details={"phase": 2},
            )
        )
        return workspace

    @router.post(
        "/claims/{claim_id}/documents",
        response_model=DocumentView,
        status_code=status.HTTP_201_CREATED,
        tags=["documents"],
    )
    async def upload_document(
        claim_id: UUID,
        request: Request,
        actor: ActorDependency,
        session: SessionDependency,
        file: Annotated[UploadFile, File()],
    ) -> DocumentView:
        authorize(actor, Action.DOCUMENT_UPLOAD)
        enforce_limit(
            request,
            scope="upload",
            subject=f"{actor.tenant_id}:{actor.user_id}",
            limit=request.app.state.components.settings.upload_rate_limit,
        )
        content = await file.read(MAX_DOCUMENT_BYTES + 1)
        service = DocumentIngestionService(session, request.app.state.components.object_storage)
        try:
            document = await service.ingest(
                claim_id=claim_id,
                actor=actor,
                filename=file.filename or "uploaded-document",
                declared_mime=file.content_type,
                content=content,
                correlation_id=request.state.correlation_id,
            )
        except LookupError as exc:
            raise ResourceNotFoundError(str(exc)) from exc
        except IngestionRejectedError as exc:
            raise DocumentValidationError(str(exc), exc.code) from exc
        except DuplicateDocumentError as exc:
            raise ResourceConflictError(
                f"Identical document already exists as {exc.document_id}."
            ) from exc
        detail = PlatformService(session).document_detail(document.id, actor)
        assert detail is not None
        return detail.document

    @router.get("/documents/{document_id}", response_model=DocumentDetailView, tags=["documents"])
    def document_detail(
        document_id: UUID, actor: ActorDependency, session: SessionDependency
    ) -> DocumentDetailView:
        authorize(actor, Action.DOCUMENT_READ)
        detail = PlatformService(session).document_detail(document_id, actor)
        if detail is None:
            raise ResourceNotFoundError("document not found")
        return detail

    @router.get("/documents/{document_id}/original", tags=["documents"])
    async def document_original(
        document_id: UUID,
        request: Request,
        actor: ActorDependency,
        session: SessionDependency,
    ) -> Response:
        authorize(actor, Action.DOCUMENT_READ)
        document = DocumentRepository(session).get_for_actor(document_id, actor)
        if document is None:
            raise ResourceNotFoundError("document not found")
        try:
            content = await request.app.state.components.object_storage.get_bytes(
                document.storage_key
            )
        except (KeyError, FileNotFoundError) as exc:
            raise ResourceNotFoundError("original document object is unavailable") from exc
        return Response(
            content=content,
            media_type=document.detected_mime_type,
            headers={"Content-Disposition": f'inline; filename="{document.name}"'},
        )

    @router.post("/documents/{document_id}/retry", response_model=DocumentView, tags=["documents"])
    async def retry_document(
        document_id: UUID,
        request: Request,
        actor: ActorDependency,
        session: SessionDependency,
    ) -> DocumentView:
        authorize(actor, Action.DOCUMENT_UPLOAD)
        if DocumentRepository(session).get_for_actor(document_id, actor) is None:
            raise ResourceNotFoundError("document not found")
        processed = await DocumentIngestionService(
            session, request.app.state.components.object_storage
        ).process(document_id, actor, None, request.state.correlation_id)
        detail = PlatformService(session).document_detail(processed.id, actor)
        assert detail is not None
        return detail.document

    def citation(item: RetrievedEvidence, claim_id: UUID) -> CitationView:
        chunk = item.chunk
        return CitationView(
            id=stable_citation_id(chunk.chunk_identifier),
            claim_id=claim_id,
            document_id=chunk.document_id,
            document_name=chunk.document.name,
            document_type=chunk.document_type,
            page_number=chunk.page_number,
            chunk_identifier=chunk.chunk_identifier,
            chunk_ordinal=chunk.chunk_ordinal,
            source_start=chunk.source_start,
            source_end=chunk.source_end,
            source_checksum=chunk.source_checksum,
            page_checksum=chunk.page_checksum,
            excerpt=chunk.normalized_text,
            policy_edition=chunk.policy_edition,
            applicability_status=item.applicability_status,
            injection_risk=chunk.injection_risk,
            retrieval_rank=item.rank,
            retrieval_score=round(item.score, 8),
            lexical_score=round(item.lexical_score, 8),
            vector_score=round(item.vector_score, 8),
            retrieval_method=FUSION_VERSION,
            source_url=f"/documents/{chunk.document_id}?page={chunk.page_number}#page-{chunk.page_number}",
        )

    @router.post(
        "/claims/{claim_id}/evidence/search",
        response_model=EvidenceSearchView,
        tags=["retrieval"],
    )
    def search_evidence(
        claim_id: UUID,
        payload: EvidenceQuery,
        request: Request,
        actor: ActorDependency,
        session: SessionDependency,
    ) -> EvidenceSearchView:
        authorize(actor, Action.RETRIEVAL_QUERY)
        enforce_limit(
            request,
            scope="retrieval",
            subject=f"{actor.tenant_id}:{actor.user_id}",
            limit=request.app.state.components.settings.retrieval_rate_limit,
        )
        try:
            result = RetrievalService(session).retrieve(
                claim_id=claim_id, actor=actor, question=payload.question, limit=payload.limit
            )
        except LookupError as exc:
            raise ResourceNotFoundError("claim not found") from exc
        citations = [citation(item, claim_id) for item in result.evidence]
        AuditRepository(session).append(
            AuditEventModel(
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                action="retrieval.search.completed",
                resource_type="claim",
                resource_id=str(claim_id),
                outcome="success",
                correlation_id=request.state.correlation_id,
                details={
                    "question_sha256": hashlib.sha256(payload.question.encode()).hexdigest(),
                    "question_length": len(payload.question),
                    "returned_chunks": len(citations),
                    "retrieval_configuration": FUSION_VERSION,
                    "duration_ms": round(result.duration_ms, 2),
                    "embedding_duration_ms": round(result.embedding_duration_ms, 2),
                },
            )
        )
        descriptor = DeterministicHashEmbeddingProvider.descriptor
        return EvidenceSearchView(
            question=payload.question,
            citations=citations,
            retrieval_configuration=FUSION_VERSION,
            embedding_provider=descriptor.provider,
            embedding_model=descriptor.model,
            embedding_version=descriptor.version,
            candidate_chunks=result.candidate_count,
            returned_chunks=len(citations),
            retrieval_duration_ms=round(result.duration_ms, 2),
            embedding_duration_ms=round(result.embedding_duration_ms, 2),
            correlation_id=request.state.correlation_id,
        )

    @router.post(
        "/claims/{claim_id}/questions",
        response_model=GroundedAnswerView,
        tags=["retrieval"],
    )
    def grounded_question(
        claim_id: UUID,
        payload: EvidenceQuery,
        request: Request,
        actor: ActorDependency,
        session: SessionDependency,
    ) -> GroundedAnswerView:
        authorize(actor, Action.RETRIEVAL_QUERY)
        enforce_limit(
            request,
            scope="grounded_question",
            subject=f"{actor.tenant_id}:{actor.user_id}",
            limit=request.app.state.components.settings.retrieval_rate_limit,
        )
        try:
            result = GroundedAnswerService(session).answer(
                claim_id=claim_id,
                actor=actor,
                question=payload.question,
                limit=payload.limit,
            )
        except LookupError as exc:
            raise ResourceNotFoundError("claim not found") from exc
        citations = [citation(item, claim_id) for item in result.retrieval.evidence]
        conflicts = [
            ConflictSummaryView(
                fact_type=conflict.fact_type,
                left_document_name=conflict.left_fact.document.name,
                left_value=conflict.left_fact.normalized_value,
                right_document_name=conflict.right_fact.document.name,
                right_value=conflict.right_fact.normalized_value,
            )
            for conflict in DocumentRepository(session).conflicts(claim_id, actor.tenant_id)
        ]
        AuditRepository(session).append(
            AuditEventModel(
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                action="retrieval.answer.completed",
                resource_type="claim",
                resource_id=str(claim_id),
                outcome="abstained" if result.state == "insufficient_evidence" else "success",
                correlation_id=request.state.correlation_id,
                details={
                    "question_sha256": hashlib.sha256(payload.question.encode()).hexdigest(),
                    "question_length": len(payload.question),
                    "state": result.state,
                    "returned_chunks": len(citations),
                    "retrieval_configuration": FUSION_VERSION,
                    "generator_provider": result.provider,
                    "generator_model": result.model,
                    "retrieval_duration_ms": round(result.retrieval.duration_ms, 2),
                    "embedding_duration_ms": round(result.retrieval.embedding_duration_ms, 2),
                    "generation_duration_ms": round(result.generation_duration_ms, 2),
                },
            )
        )
        return GroundedAnswerView(
            question=payload.question,
            state=result.state,
            answer=result.answer,
            answerable=result.state in {"answerable", "conflicting_evidence", "ambiguous_evidence"},
            citations=citations,
            retrieved_evidence=citations,
            conflicts=conflicts,
            ambiguity_indicators=result.ambiguity_indicators,
            missing_information=result.missing_information,
            human_review_required=result.human_review_required,
            applicable_policy_version=result.retrieval.claim.policy.edition,
            retrieval_configuration=FUSION_VERSION,
            generator_provider=result.provider,
            generator_model=result.model,
            generator_version=result.model_version,
            retrieval_duration_ms=round(result.retrieval.duration_ms, 2),
            embedding_duration_ms=round(result.retrieval.embedding_duration_ms, 2),
            generation_duration_ms=round(result.generation_duration_ms, 2),
            correlation_id=request.state.correlation_id,
        )

    @router.get("/review-tasks", response_model=list[ReviewTaskView], tags=["reviews"])
    def reviews(
        actor: ActorDependency,
        session: SessionDependency,
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
        offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    ) -> list[ReviewTaskView]:
        authorize(actor, Action.REVIEW_QUEUE_READ)
        return PlatformService(session).review_queue(actor, limit=limit, offset=offset)

    def brief_service(request: Request, session: SessionDependency) -> ClaimEvidenceBriefService:
        settings = request.app.state.components.settings
        return ClaimEvidenceBriefService(
            session,
            request.app.state.components.model_provider,
            timeout_seconds=settings.model_timeout_seconds,
            max_retries=settings.model_max_retries,
            max_input_characters=settings.model_max_input_characters,
            max_output_tokens=settings.model_max_output_tokens,
        )

    @router.post(
        "/claims/{claim_id}/briefs",
        response_model=ClaimEvidenceBriefView,
        status_code=status.HTTP_201_CREATED,
        tags=["model-assistance"],
    )
    def create_brief(
        claim_id: UUID,
        payload: ClaimEvidenceBriefRequest,
        request: Request,
        actor: ActorDependency,
        session: SessionDependency,
    ) -> ClaimEvidenceBriefView:
        authorize(actor, Action.BRIEF_CREATE)
        enforce_limit(
            request,
            scope="model_assistance",
            subject=f"{actor.tenant_id}:{actor.user_id}",
            limit=request.app.state.components.settings.model_rate_limit,
        )
        try:
            return brief_service(request, session).create(
                claim_id=claim_id,
                actor=actor,
                task=payload.task,
                idempotency_key=payload.idempotency_key,
                correlation_id=request.state.correlation_id,
            )
        except BriefNotFoundError as exc:
            raise ResourceNotFoundError(str(exc)) from exc
        except BriefConflictError as exc:
            raise ResourceConflictError(str(exc)) from exc
        except BriefGenerationError as exc:
            raise ResourceConflictError(
                "The model-assisted brief was rejected by application safety validation."
            ) from exc

    @router.get(
        "/claims/{claim_id}/briefs/latest",
        response_model=ClaimEvidenceBriefView | None,
        tags=["model-assistance"],
    )
    def latest_brief(
        claim_id: UUID,
        request: Request,
        actor: ActorDependency,
        session: SessionDependency,
    ) -> ClaimEvidenceBriefView | None:
        authorize(actor, Action.BRIEF_READ)
        try:
            return brief_service(request, session).latest(claim_id, actor)
        except BriefNotFoundError as exc:
            raise ResourceNotFoundError(str(exc)) from exc

    @router.get(
        "/briefs/{brief_id}",
        response_model=ClaimEvidenceBriefView,
        tags=["model-assistance"],
    )
    def get_brief(
        brief_id: UUID,
        request: Request,
        actor: ActorDependency,
        session: SessionDependency,
    ) -> ClaimEvidenceBriefView:
        authorize(actor, Action.BRIEF_READ)
        service = brief_service(request, session)
        try:
            return service.view(service.get(brief_id, actor), actor)
        except BriefNotFoundError as exc:
            raise ResourceNotFoundError(str(exc)) from exc

    def workflow_or_not_found(
        workflow_id: UUID, actor: ActorDependency, session: SessionDependency
    ) -> WorkflowRunModel:
        try:
            return ControlledWorkflowService(session).get(workflow_id, actor)
        except WorkflowNotFoundError as exc:
            raise ResourceNotFoundError(str(exc)) from exc

    @router.post(
        "/claims/{claim_id}/workflows",
        response_model=ControlledWorkflowView,
        status_code=status.HTTP_201_CREATED,
        tags=["workflows"],
    )
    def start_workflow(
        claim_id: UUID,
        payload: WorkflowStartRequest,
        request: Request,
        actor: ActorDependency,
        session: SessionDependency,
    ) -> ControlledWorkflowView:
        authorize(actor, Action.WORKFLOW_START)
        try:
            return ControlledWorkflowService(session).start(
                claim_id=claim_id,
                actor=actor,
                task=payload.task,
                idempotency_key=payload.idempotency_key,
                correlation_id=request.state.correlation_id,
            )
        except WorkflowNotFoundError as exc:
            raise ResourceNotFoundError(str(exc)) from exc
        except WorkflowConflictError as exc:
            raise ResourceConflictError(str(exc)) from exc
        except WorkflowExecutionError as exc:
            raise ResourceConflictError(str(exc)) from exc

    @router.get(
        "/claims/{claim_id}/workflows/latest",
        response_model=ControlledWorkflowView | None,
        tags=["workflows"],
    )
    def latest_workflow(
        claim_id: UUID, actor: ActorDependency, session: SessionDependency
    ) -> ControlledWorkflowView | None:
        authorize(actor, Action.WORKFLOW_READ)
        try:
            return ControlledWorkflowService(session).latest(claim_id, actor)
        except WorkflowNotFoundError as exc:
            raise ResourceNotFoundError(str(exc)) from exc

    @router.get(
        "/workflows/{workflow_id}", response_model=ControlledWorkflowView, tags=["workflows"]
    )
    def get_workflow(
        workflow_id: UUID, actor: ActorDependency, session: SessionDependency
    ) -> ControlledWorkflowView:
        authorize(actor, Action.WORKFLOW_READ)
        return ControlledWorkflowService(session).view(
            workflow_or_not_found(workflow_id, actor, session)
        )

    @router.get(
        "/workflows/{workflow_id}/history",
        response_model=WorkflowHistoryView,
        tags=["workflows"],
    )
    def workflow_history(
        workflow_id: UUID, actor: ActorDependency, session: SessionDependency
    ) -> WorkflowHistoryView:
        authorize(actor, Action.WORKFLOW_READ)
        service = ControlledWorkflowService(session)
        return service.history(workflow_or_not_found(workflow_id, actor, session))

    @router.post(
        "/workflows/{workflow_id}/review",
        response_model=ControlledWorkflowView,
        tags=["workflows"],
    )
    def review_workflow(
        workflow_id: UUID,
        payload: WorkflowReviewRequest,
        actor: ActorDependency,
        session: SessionDependency,
    ) -> ControlledWorkflowView:
        authorize(actor, Action.WORKFLOW_REVIEW)
        service = ControlledWorkflowService(session)
        workflow = workflow_or_not_found(workflow_id, actor, session)
        try:
            return service.review(
                workflow=workflow,
                actor=actor,
                action=payload.action,
                reason=payload.reason,
                expected_version=payload.expected_checkpoint_version,
                idempotency_key=payload.idempotency_key,
            )
        except WorkflowConflictError as exc:
            raise ResourceConflictError(str(exc)) from exc

    @router.post(
        "/workflows/{workflow_id}/cancel",
        response_model=ControlledWorkflowView,
        tags=["workflows"],
    )
    def cancel_workflow(
        workflow_id: UUID, actor: ActorDependency, session: SessionDependency
    ) -> ControlledWorkflowView:
        authorize(actor, Action.WORKFLOW_CANCEL)
        service = ControlledWorkflowService(session)
        try:
            return service.cancel(workflow_or_not_found(workflow_id, actor, session), actor)
        except WorkflowConflictError as exc:
            raise ResourceConflictError(str(exc)) from exc

    @router.post(
        "/workflows/{workflow_id}/retry",
        response_model=ControlledWorkflowView,
        tags=["workflows"],
    )
    def retry_workflow(
        workflow_id: UUID,
        payload: WorkflowRetryRequest,
        actor: ActorDependency,
        session: SessionDependency,
    ) -> ControlledWorkflowView:
        authorize(actor, Action.WORKFLOW_RETRY)
        service = ControlledWorkflowService(session)
        try:
            return service.retry(
                workflow_or_not_found(workflow_id, actor, session),
                actor,
                payload.idempotency_key,
            )
        except WorkflowConflictError as exc:
            raise ResourceConflictError(str(exc)) from exc

    @router.get("/operations/summary", response_model=OperationsSummaryView, tags=["operations"])
    def operations(actor: ActorDependency, session: SessionDependency) -> OperationsSummaryView:
        authorize(actor, Action.OPERATIONS_READ)
        return PlatformService(session).operations(actor)

    @router.post("/system/jobs/smoke", response_model=JobView, tags=["system"])
    async def enqueue_smoke(
        payload: SmokeJobRequest, request: Request, actor: ActorDependency
    ) -> JobView:
        authorize(actor, Action.SYSTEM_JOB_CREATE)
        job = Job(
            id=str(uuid.uuid4()),
            kind="platform.smoke",
            payload={"message": payload.message},
            correlation_id=request.state.correlation_id,
        )
        await request.app.state.components.job_queue.enqueue(job)
        return JobView(id=job.id, status="queued")

    @router.get("/system/jobs/{job_id}", response_model=JobView, tags=["system"])
    async def job_result(job_id: str, request: Request, actor: ActorDependency) -> JobView:
        authorize(actor, Action.SYSTEM_JOB_CREATE)
        result = await request.app.state.components.job_queue.result(job_id)
        return JobView(id=job_id, status="completed" if result else "pending", result=result)

    return router
