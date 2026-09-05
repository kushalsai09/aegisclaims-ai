import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import ClaimsView from "@/views/ClaimsView.vue";

afterEach(() => vi.unstubAllGlobals());

describe("ClaimsView", () => {
  it("supports real search and workflow filtering over authorized claims", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [
          {
            id: "1",
            claim_number: "HVC-SYN-0001",
            loss_date: "2026-08-14",
            loss_type: "Wind damage",
            property_address: "1 Example Lane",
            status: "open",
            policy_number: "POL-1",
            workflow_status: "completed",
            assigned_to: "Avery Morgan",
            updated_at: "2026-08-26T12:00:00Z",
          },
          {
            id: "2",
            claim_number: "HVC-SYN-0002",
            loss_date: "2026-08-15",
            loss_type: "Water damage",
            property_address: "2 Example Lane",
            status: "open",
            policy_number: "POL-2",
            workflow_status: "awaiting_human_review",
            assigned_to: "Jordan Lee",
            updated_at: "2026-08-27T12:00:00Z",
          },
        ],
      }),
    );
    const wrapper = mount(ClaimsView, {
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("2 of 2 claims");

    await wrapper.find('input[type="search"]').setValue("Water");
    expect(wrapper.text()).toContain("HVC-SYN-0002");
    expect(wrapper.text()).not.toContain("HVC-SYN-0001");

    await wrapper.find('input[type="search"]').setValue("");
    await wrapper.findAll("select")[0]?.setValue("completed");
    expect(wrapper.text()).toContain("HVC-SYN-0001");
    expect(wrapper.text()).not.toContain("HVC-SYN-0002");
    wrapper.unmount();
  });
});
