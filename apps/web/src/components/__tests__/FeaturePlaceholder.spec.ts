import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import FeaturePlaceholder from "@/components/FeaturePlaceholder.vue";

describe("FeaturePlaceholder", () => {
  it("labels future AI capability without inventing output", () => {
    const wrapper = mount(FeaturePlaceholder, {
      props: {
        title: "Support Assessment",
        description:
          "No confidence score or support signals are generated in Phase 2.",
      },
    });

    expect(wrapper.get("h3").text()).toBe("Support Assessment");
    expect(wrapper.text()).toContain("Not implemented");
    expect(wrapper.text()).toContain("No confidence score");
    wrapper.unmount();
  });
});
