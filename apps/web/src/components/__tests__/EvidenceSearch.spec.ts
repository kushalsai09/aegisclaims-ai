import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import EvidenceSearch from "@/components/EvidenceSearch.vue";

const { api } = vi.hoisted(() => ({ api: vi.fn() }));
vi.mock("@/services/api", async () => {
  const actual =
    await vi.importActual<typeof import("@/services/api")>("@/services/api");
  return { ...actual, api };
});

describe("EvidenceSearch", () => {
  it("renders a grounded result with a navigable citation and safety boundary", async () => {
    api.mockResolvedValue({
      question: "What address is stated?",
      state: "answerable",
      answer: "Grounded evidence: Property Address: 200 Test Cedar Place.",
      answerable: true,
      citations: [
        {
          id: "CIT-1234",
          document_name: "Untrusted Correspondence.pdf",
          page_number: 1,
          excerpt: "Property Address: 200 Test Cedar Place",
          source_url: "/documents/document-1?page=1#page-1",
          retrieval_rank: 1,
          retrieval_method: "hybrid_rrf_k60_v1",
          applicability_status: "applicable",
          injection_risk: true,
        },
      ],
      retrieved_evidence: [],
      conflicts: [],
      ambiguity_indicators: [],
      missing_information: [],
      human_review_required: true,
      applicable_policy_version: "2026-SYN-A",
      retrieval_configuration: "hybrid_rrf_k60_v1",
      generator_provider: "local_deterministic",
      generator_model: "extractive_grounded_answer",
      generator_version: "extractive_grounded_answer_v1",
      correlation_id: "correlation-1",
    });
    const wrapper = mount(EvidenceSearch, {
      props: { claimId: "claim-1" },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });
    await wrapper.get("textarea").setValue("What address is stated?");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(api).toHaveBeenCalledWith(
      "/claims/claim-1/questions",
      expect.any(Object),
    );
    expect(wrapper.text()).toContain("Grounded evidence");
    expect(wrapper.text()).toContain("CIT-1234");
    expect(wrapper.text()).toContain("Untrusted instructions detected");
    expect(wrapper.text()).toContain("Human review is already required");
    wrapper.unmount();
  });

  it("renders an insufficient-evidence state without decision language", async () => {
    api.mockResolvedValue({
      state: "insufficient_evidence",
      answer:
        "The available claim evidence is insufficient to answer this question.",
      answerable: false,
      citations: [],
      ambiguity_indicators: [],
      missing_information: ["estimate"],
      human_review_required: false,
      applicable_policy_version: "2026-SYN-A",
      retrieval_configuration: "hybrid_rrf_k60_v1",
      correlation_id: "correlation-2",
    });
    const wrapper = mount(EvidenceSearch, {
      props: { claimId: "claim-1" },
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });
    await wrapper.get("textarea").setValue("What estimate is documented?");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("Insufficient evidence");
    expect(wrapper.text()).toContain("Missing information");
    expect(wrapper.text()).not.toContain("Approve claim");
    wrapper.unmount();
  });
});
