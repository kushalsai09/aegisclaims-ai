import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import ReviewQueueView from "@/views/ReviewQueueView.vue";

const { api } = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("@/services/api", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return { ...actual, api };
});

describe("ReviewQueueView", () => {
  it("shows workflow escalation reason and safety indicators", async () => {
    api.mockResolvedValue([
      {
        id: "task-1",
        claim_id: "claim-1",
        status: "open",
        reason_code: "phase4_workflow_review",
        reason: "Material evidence conflict",
        created_at: "2026-08-26T12:00:00Z",
        workflow_id: "workflow-1",
        workflow_status: "awaiting_human_review",
        safety_flags: ["conflict", "untrusted_content"],
      },
    ]);
    const wrapper = mount(ReviewQueueView, {
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("Material evidence conflict");
    expect(wrapper.text()).toContain("conflict");
    expect(wrapper.text()).toContain("untrusted content");
    expect(wrapper.text()).toContain("awaiting human review");
  });
});
