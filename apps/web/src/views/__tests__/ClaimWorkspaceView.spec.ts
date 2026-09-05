import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import ClaimWorkspaceView from "@/views/ClaimWorkspaceView.vue";

const { api, uploadDocument } = vi.hoisted(() => ({
  api: vi.fn(),
  uploadDocument: vi.fn(),
}));
vi.mock("@/services/api", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return { ...actual, api, uploadDocument };
});
vi.mock("vue-router", () => ({
  useRoute: () => ({ params: { id: "claim-1" } }),
  RouterLink: { template: "<a><slot /></a>" },
}));

const workspace = {
  claim: {
    id: "claim-1",
    claim_number: "HVC-SYN-2026-00017",
    loss_date: "2026-08-14",
    loss_type: "Wind damage",
    property_address: "1842 Example Ridge Lane",
    status: "open",
    description: "Synthetic description",
    version: 1,
  },
  policy: {
    id: "policy-1",
    policy_number: "HVS-HO-000042",
    product_code: "HO-SYN-01",
    product_name: "HarborView HomeSecure",
    edition: "2026-SYN-A",
    effective_from: "2026-01-01",
    effective_to: "2027-01-01",
    status: "active",
    synthetic_label: "SYNTHETIC DEMONSTRATION DATA",
  },
  documents: [
    {
      id: "document-1",
      name: "Synthetic Notice.txt",
      document_type: "notice_of_loss",
      content_type: "text/plain",
      detected_mime_type: "text/plain",
      processing_status: "ready",
      extraction_status: "extracted",
      page_count: 1,
      size_bytes: 120,
      checksum_sha256: "a".repeat(64),
      uploaded_by: "Avery Morgan",
      uploaded_at: "2026-08-26T08:00:00Z",
      injection_risk: false,
      synthetic_label: "SYNTHETIC DEMONSTRATION DATA",
      created_at: "2026-08-26T08:00:00Z",
    },
  ],
  conflicts: [
    {
      id: "conflict-1",
      fact_type: "reported_loss_date",
      status: "conflict_detected",
      detection_method: "deterministic_exact_v1",
      left_document_name: "Notice of Loss.txt",
      right_document_name: "Contractor Estimate.txt",
      left: { normalized_value: "2026-08-18" },
      right: { normalized_value: "2026-08-12" },
    },
  ],
  workflow: null,
  human_review_status: "not_required",
  future_sections: [
    {
      key: "ai_summary",
      title: "AI Summary",
      status: "not_implemented",
      description: "No AI summary is generated in Phase 2.",
    },
  ],
  synthetic_notice: "SYNTHETIC DEMONSTRATION DATA",
};

describe("ClaimWorkspaceView", () => {
  it("renders real document state, conflicts, and future AI boundaries", async () => {
    api.mockResolvedValue(workspace);
    const wrapper = mount(ClaimWorkspaceView, {
      global: {
        stubs: {
          RouterLink: { template: "<a><slot /></a>" },
          WorkflowPanel: { template: "<section>Controlled workflow</section>" },
        },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain("Synthetic Notice.txt");
    expect(wrapper.text()).toContain("uploaded by Avery Morgan");
    expect(wrapper.text()).toContain("Conflicts detected");
    expect(wrapper.text()).toContain("2026-08-18");
    expect(wrapper.text()).toContain("Notice of Loss.txt");
    expect(wrapper.text()).toContain("Contractor Estimate.txt");
    expect(wrapper.text()).toContain("AI Summary");
    expect(wrapper.text()).toContain("Not implemented");
    wrapper.unmount();
  });
});
