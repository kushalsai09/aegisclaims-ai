import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import SignInView from "@/views/SignInView.vue";

const push = vi.fn();
vi.mock("vue-router", () => ({ useRouter: () => ({ push }) }));

afterEach(() => {
  vi.unstubAllGlobals();
  push.mockReset();
});

describe("SignInView", () => {
  it("renders professional credentials without role selection and signs in", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        user: {
          id: "60000000-0000-4000-8000-000000000001",
          first_name: "Avery",
          last_name: "Morgan",
          display_name: "Avery Morgan",
          email: "avery.morgan@example.invalid",
          roles: ["claims_adjuster"],
          organization: "HarborView Mutual Demonstration Organization",
          account_status: "active",
          created_at: null,
          last_login_at: null,
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const wrapper = mount(SignInView);
    expect(wrapper.text()).toContain("Sign in to HarborView");
    expect(wrapper.find('input[type="email"]').exists()).toBe(true);
    expect(wrapper.find('input[type="password"]').exists()).toBe(true);
    expect(wrapper.text()).not.toContain("Administrator");
    expect(wrapper.text()).not.toContain("Choose a synthetic employee");

    await wrapper
      .find('input[type="email"]')
      .setValue("avery.morgan@example.invalid");
    await wrapper
      .find('input[type="password"]')
      .setValue("development-password");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/auth/login"),
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(String(request.body)).not.toContain("role");
    expect(push).toHaveBeenCalledWith({ name: "dashboard" });
    wrapper.unmount();
  });

  it("explains a throttled sign-in without exposing provider details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 429,
        json: async () => ({ detail: "Too many requests. Try again later." }),
      }),
    );
    const wrapper = mount(SignInView);
    await wrapper.find('input[type="email"]').setValue("avery.morgan@example.invalid");
    await wrapper.find('input[type="password"]').setValue("wrong-password");
    await wrapper.find("form").trigger("submit");
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toBe(
      "Too many sign-in attempts. Please wait and try again.",
    );
    wrapper.unmount();
  });
});
