<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { authState, hasRole, signOut } from "@/services/auth";

const route = useRoute();
const router = useRouter();
const mobileOpen = ref(false);
const accountOpen = ref(false);
const mobileTrigger = ref<HTMLButtonElement | null>(null);
const initials = computed(() =>
  authState.session?.user.display_name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2),
);
const roleLabel = computed(() =>
  authState.session?.user.roles[0]?.replaceAll("_", " "),
);

async function handleSignOut() {
  accountOpen.value = false;
  await signOut();
  await router.push({ name: "sign-in" });
}

async function closeMobileNavigation(restoreFocus = true) {
  mobileOpen.value = false;
  if (restoreFocus) {
    await nextTick();
    mobileTrigger.value?.focus();
  }
}
</script>

<template>
  <div class="app-frame">
    <header class="mobile-header">
      <button
        ref="mobileTrigger"
        class="icon-button"
        aria-label="Open navigation"
        aria-controls="primary-sidebar"
        :aria-expanded="mobileOpen"
        @click="mobileOpen = true"
      >
        <span aria-hidden="true">☰</span>
      </button>
      <RouterLink to="/" class="mobile-brand">HarborView Claims</RouterLink>
      <span class="avatar avatar--small" aria-hidden="true">{{
        initials
      }}</span>
    </header>
    <div
      v-if="mobileOpen"
      class="nav-scrim"
      aria-hidden="true"
      @click="closeMobileNavigation()"
    ></div>
    <aside
      id="primary-sidebar"
      class="sidebar"
      :class="{ 'sidebar--open': mobileOpen }"
      aria-label="Primary navigation"
      @keydown.esc="closeMobileNavigation()"
    >
      <div class="brand-block">
        <div class="brand-mark" aria-hidden="true">HV</div>
        <div><strong>HarborView</strong><span>Claims Operations</span></div>
        <button
          class="sidebar-close"
          aria-label="Close navigation"
          @click="closeMobileNavigation()"
        >
          ×
        </button>
      </div>
      <nav class="primary-nav" aria-label="Workspace">
        <RouterLink
          to="/"
          :class="{ active: route.name === 'dashboard' }"
          @click="mobileOpen = false"
        >
          <span class="nav-icon" aria-hidden="true">01</span
          ><span>My Work</span>
        </RouterLink>
        <RouterLink
          to="/claims"
          :class="{
            active:
              route.name === 'claims' ||
              route.name === 'claim' ||
              route.name === 'document',
          }"
          @click="mobileOpen = false"
        >
          <span class="nav-icon" aria-hidden="true">02</span><span>Claims</span>
        </RouterLink>
        <RouterLink
          v-if="hasRole('supervisor', 'admin')"
          to="/reviews"
          :class="{ active: route.name === 'reviews' }"
          @click="mobileOpen = false"
        >
          <span class="nav-icon" aria-hidden="true">03</span
          ><span>Reviews</span>
        </RouterLink>
      </nav>
      <div v-if="hasRole('compliance_reviewer', 'admin')" class="nav-group">
        <span>Oversight</span>
        <nav aria-label="Oversight">
          <RouterLink
            to="/operations"
            :class="{ active: route.name === 'operations' }"
            @click="mobileOpen = false"
            >Operations</RouterLink
          >
          <RouterLink
            to="/evaluation"
            :class="{ active: route.name === 'evaluation' }"
            @click="mobileOpen = false"
            >Evaluation</RouterLink
          >
        </nav>
      </div>
      <div class="sidebar-footer">
        <div class="environment-banner">
          <span></span>Local · Synthetic data
        </div>
        <button
          class="account-trigger"
          :aria-expanded="accountOpen"
          aria-controls="account-menu"
          @click="accountOpen = !accountOpen"
        >
          <span class="avatar" aria-hidden="true">{{ initials }}</span>
          <span
            ><strong>{{ authState.session?.user.display_name }}</strong
            ><small>{{ roleLabel }}</small></span
          >
          <span aria-hidden="true">⌃</span>
        </button>
        <div v-if="accountOpen" id="account-menu" class="account-menu">
          <div>
            <strong>{{ authState.session?.user.email }}</strong
            ><span>{{ authState.session?.user.organization }}</span>
          </div>
          <button @click="handleSignOut">Sign out</button>
        </div>
      </div>
    </aside>
    <main
      id="main-content"
      class="main-content"
      tabindex="-1"
      :inert="mobileOpen ? true : undefined"
    >
      <slot />
    </main>
  </div>
</template>
