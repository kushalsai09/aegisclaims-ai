import { createRouter, createWebHistory } from "vue-router";
import { authState, hasRole, initializeSession } from "@/services/auth";
import ClaimsView from "@/views/ClaimsView.vue";
import ClaimWorkspaceView from "@/views/ClaimWorkspaceView.vue";
import DashboardView from "@/views/DashboardView.vue";
import DocumentDetailView from "@/views/DocumentDetailView.vue";
import EvaluationView from "@/views/EvaluationView.vue";
import OperationsView from "@/views/OperationsView.vue";
import ReviewQueueView from "@/views/ReviewQueueView.vue";
import SignInView from "@/views/SignInView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/sign-in",
      name: "sign-in",
      component: SignInView,
      meta: { public: true },
    },
    { path: "/", name: "dashboard", component: DashboardView },
    { path: "/claims", name: "claims", component: ClaimsView },
    { path: "/claims/:id", name: "claim", component: ClaimWorkspaceView },
    {
      path: "/documents/:id",
      name: "document",
      component: DocumentDetailView,
    },
    { path: "/reviews", name: "reviews", component: ReviewQueueView },
    { path: "/operations", name: "operations", component: OperationsView },
    { path: "/evaluation", name: "evaluation", component: EvaluationView },
    {
      path: "/:pathMatch(.*)*",
      name: "not-found",
      component: () => import("@/views/NotFoundView.vue"),
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

router.beforeEach(async (to) => {
  await initializeSession();
  if (!to.meta.public && !authState.session) return { name: "sign-in" };
  if (to.name === "sign-in" && authState.session) return { name: "dashboard" };
  if (to.name === "reviews" && !hasRole("supervisor", "admin"))
    return { name: "dashboard" };
  if (
    (to.name === "operations" || to.name === "evaluation") &&
    !hasRole("compliance_reviewer", "admin")
  )
    return { name: "dashboard" };
  return true;
});

export default router;
