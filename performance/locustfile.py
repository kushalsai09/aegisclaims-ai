from __future__ import annotations

import itertools

from locust import HttpUser, between, task


class ClaimsOperationsUser(HttpUser):
    """Read-heavy internal-claims workload with bounded governed retrieval."""

    wait_time = between(0.5, 1.5)
    claim_id = ""
    document_id = ""
    _user_numbers = itertools.count()
    _emails = (
        "avery.morgan@example.invalid",
        "jordan.lee@example.invalid",
        "riley.chen@example.invalid",
        "casey.patel@example.invalid",
    )

    def on_start(self) -> None:
        login = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": self._emails[next(self._user_numbers) % len(self._emails)],
                "password": "HarborView!Local2026",
                "remember": False,
            },
            name="POST /api/v1/auth/login",
        )
        login.raise_for_status()
        claims = self.client.get("/api/v1/claims?limit=20&offset=0", name="GET /api/v1/claims")
        claims.raise_for_status()
        self.claim_id = claims.json()[0]["id"]
        workspace = self.client.get(
            f"/api/v1/claims/{self.claim_id}", name="GET /api/v1/claims/:id"
        )
        workspace.raise_for_status()
        self.document_id = workspace.json()["documents"][0]["id"]
        question = self.client.post(
            f"/api/v1/claims/{self.claim_id}/questions",
            json={"question": "What property address is documented?", "limit": 5},
            name="POST /api/v1/claims/:id/questions",
        )
        question.raise_for_status()

    @task(5)
    def list_claims(self) -> None:
        self.client.get("/api/v1/claims?limit=20&offset=0", name="GET /api/v1/claims")

    @task(4)
    def claim_workspace(self) -> None:
        self.client.get(f"/api/v1/claims/{self.claim_id}", name="GET /api/v1/claims/:id")

    @task(3)
    def document_detail(self) -> None:
        self.client.get(f"/api/v1/documents/{self.document_id}", name="GET /api/v1/documents/:id")

    @task(2)
    def dashboard(self) -> None:
        self.client.get("/api/v1/dashboard", name="GET /api/v1/dashboard")

    @task(1)
    def evidence_search(self) -> None:
        self.client.post(
            f"/api/v1/claims/{self.claim_id}/evidence/search",
            json={"question": "What property address is documented?", "limit": 5},
            name="POST /api/v1/claims/:id/evidence/search",
        )

    @task(1)
    def latest_brief_and_workflow(self) -> None:
        self.client.get(
            f"/api/v1/claims/{self.claim_id}/briefs/latest",
            name="GET /api/v1/claims/:id/briefs/latest",
        )
        self.client.get(
            f"/api/v1/claims/{self.claim_id}/workflows/latest",
            name="GET /api/v1/claims/:id/workflows/latest",
        )
