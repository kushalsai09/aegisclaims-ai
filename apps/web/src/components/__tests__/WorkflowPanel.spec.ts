import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import WorkflowPanel from "@/components/WorkflowPanel.vue";
import { authState } from "@/services/auth";

const { api } = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("@/services/api", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return { ...actual, api };
});

const workflow = {
  id: "workflow-1",
  claim_id: "claim-1",
  workflow_type: "claim_evidence_review",
  workflow_version: "phase4-claim-evidence-review-v1",
  status: "awaiting_human_review",
  current_stage: "awaiting_human_review",
  checkpoint_version: 6,
  task: "Review evidence",
  applicable_policy_edition: "2026-SYN-A",
  human_review_required: true,
  approval_state: "pending",
  retry_count: 0,
  max_retries: 2,
  correlation_id: "correlation-1",
  input_fingerprint: "abc",
  error_code: null,
  error_detail: null,
  created_at: "2026-08-26T12:00:00Z",
  updated_at: "2026-08-26T12:00:00Z",
  artifact: {
    established_evidence: [],
    applicable_policy_evidence: [],
    conflicting_evidence: [
      {
        fact_type: "reported_loss_date",
        left_document_name: "Notice.pdf",
        left_value: "2026-08-18",
        right_document_name: "Inspection.pdf",
        right_value: "2026-08-12",
      },
    ],
    ambiguous_evidence: ["cause_allocation_unresolved"],
    missing_information: ["estimate"],
    untrusted_content_flags: ["untrusted_document_instructions_present"],
    proposed_next_steps: ["Inspect each conflicting source."],
    human_review_reason: "material_evidence_conflict,material_ambiguity",
    citations: [
      {
        id: "CIT-123",
        document_name: "Notice.pdf",
        page_number: 1,
        excerpt: "Reported loss date: 2026-08-18",
        source_url: "/documents/document-1?page=1#page-1",
      },
    ],
    authority_notice: "SYSTEM-GENERATED PROPOSAL — evidence support only.",
    forbidden_actions: ["approve_or_deny_claim"],
  },
};

describe("WorkflowPanel", () => {
  beforeEach(() => {
    api.mockReset();
    authState.session = null;
  });

  it("separates evidence, proposals, safety flags, and human authority", async () => {
    api.mockResolvedValueOnce(workflow).mockResolvedValueOnce({
      workflow_id: "workflow-1",
      events: [
        {
          sequence: 1,
          event_type: "workflow.created",
          stage: "created",
          details: { checkpoint_version: 1 },
          created_at: "2026-08-26T12:00:00Z",
        },
      ],
    });
    const wrapper = mount(WorkflowPanel, {
      props: { claimId: "claim-1" },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("SYSTEM-GENERATED PROPOSAL");
    expect(wrapper.text()).toContain("HUMAN DECISION / ACTION");
    expect(wrapper.text()).toContain("Conflicting evidence");
    expect(wrapper.text()).toContain("Missing information");
    expect(wrapper.text()).toContain("Ambiguity requiring interpretation");
    expect(wrapper.text()).toContain(
      "Untrusted document instructions detected",
    );
    expect(wrapper.text()).toContain("CIT-123");
    expect(wrapper.text()).toContain("supervisor or administrator");
  });

  it("submits an authorized review with the current checkpoint", async () => {
    authState.session = {
      access_token: "token",
      token_type: "bearer",
      user: {
        id: "user-1",
        display_name: "Reviewer",
        email: "r@example.invalid",
        roles: ["supervisor"],
      },
    };
    api
      .mockResolvedValueOnce(workflow)
      .mockResolvedValueOnce({ workflow_id: "workflow-1", events: [] });
    const completed = {
      ...workflow,
      status: "completed",
      approval_state: "acknowledged",
      checkpoint_version: 7,
    };
    api
      .mockResolvedValueOnce(completed)
      .mockResolvedValueOnce({ workflow_id: "workflow-1", events: [] });
    const wrapper = mount(WorkflowPanel, {
      props: { claimId: "claim-1" },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });
    await flushPromises();
    await wrapper
      .get("#review-reason")
      .setValue("Reviewed all cited evidence.");
    await wrapper.get(".review-actions button").trigger("click");
    await flushPromises();
    expect(api).toHaveBeenCalledWith(
      "/workflows/workflow-1/review",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(wrapper.text()).toContain("completed");
  });

  it("renders an empty start state and recoverable error", async () => {
    api.mockResolvedValueOnce(null);
    const wrapper = mount(WorkflowPanel, {
      props: { claimId: "claim-1" },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("Start controlled workflow");
    api.mockRejectedValueOnce(new Error("offline"));
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("Workflow action needs attention");
    expect(wrapper.text()).toContain("Reload current state");
  });
});
