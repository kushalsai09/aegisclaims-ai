import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import AppShell from "@/components/AppShell.vue";
import { authState } from "@/services/auth";

vi.mock("vue-router", () => ({
  useRoute: () => ({ name: "dashboard" }),
  useRouter: () => ({ push: vi.fn() }),
  RouterLink: { template: "<a><slot /></a>" },
}));

afterEach(() => {
  authState.session = null;
});

describe("AppShell", () => {
  it("shows the account identity and hides unauthorized oversight navigation", async () => {
    authState.session = {
      user: {
        id: "1",
        first_name: "Avery",
        last_name: "Morgan",
        display_name: "Avery Morgan",
        email: "avery.morgan@example.invalid",
        roles: ["claims_adjuster"],
        organization: "HarborView Mutual",
        account_status: "active",
        created_at: null,
        last_login_at: null,
      },
    };
    const wrapper = mount(AppShell);
    expect(wrapper.text()).toContain("My Work");
    expect(wrapper.text()).toContain("Claims");
    expect(wrapper.text()).not.toContain("Reviews");
    expect(
      wrapper.findAll("a").some((link) => link.text() === "Operations"),
    ).toBe(false);

    await wrapper.get(".account-trigger").trigger("click");
    expect(wrapper.text()).toContain("avery.morgan@example.invalid");
    expect(wrapper.text()).toContain("HarborView Mutual");
    expect(wrapper.text()).toContain("Sign out");
    wrapper.unmount();
  });
});
