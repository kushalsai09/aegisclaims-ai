<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { api, ApiError } from "@/services/api";
import { setSession } from "@/services/auth";
import type { Session } from "@/types";

const email = ref("");
const password = ref("");
const remember = ref(false);
const passwordVisible = ref(false);
const submitting = ref(false);
const error = ref("");
const router = useRouter();
const oidcEnabled = import.meta.env.VITE_AUTH_MODE === "oidc";
const valid = computed(
  () => email.value.trim().includes("@") && password.value.length > 0,
);

async function signIn() {
  if (!valid.value || submitting.value) return;
  submitting.value = true;
  error.value = "";
  try {
    const session = await api<Session>("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: email.value.trim(),
        password: password.value,
        remember: remember.value,
      }),
    });
    password.value = "";
    setSession(session);
    await router.push({ name: "dashboard" });
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 403)
      error.value = caught.message;
    else if (caught instanceof ApiError && caught.status === 401)
      error.value = "The email or password is incorrect.";
    else if (caught instanceof ApiError && caught.status === 429)
      error.value = "Too many sign-in attempts. Please wait and try again.";
    else error.value = "Sign-in is temporarily unavailable. Please try again.";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <main id="main-content" class="sign-in-page">
    <section class="sign-in-story" aria-labelledby="product-title">
      <div class="story-content">
        <div class="brand-lockup">
          <span class="brand-mark brand-mark--light">HV</span> HarborView
        </div>
        <p class="story-kicker">CLAIMS OPERATIONS</p>
        <h1 id="product-title">
          Evidence at hand.<br />Decisions in human hands.
        </h1>
        <p>
          Review claim records, source documents, and governed evidence
          assistance in one secure workspace.
        </p>
        <div class="trust-row" aria-label="Product principles">
          <span>Evidence grounded</span><span>Human authorized</span
          ><span>Auditable</span>
        </div>
      </div>
    </section>
    <section class="sign-in-panel" aria-labelledby="sign-in-title">
      <form class="sign-in-card" @submit.prevent="signIn">
        <div class="sign-in-heading">
          <span class="environment-label">{{ oidcEnabled ? "Enterprise identity" : "Local development" }}</span>
          <h2 id="sign-in-title">Sign in to HarborView</h2>
          <p>Use your work account to continue.</p>
        </div>
        <div v-if="error" class="inline-alert" role="alert">{{ error }}</div>
        <template v-if="!oidcEnabled">
          <label class="field-label" for="email">Work email</label>
          <input
            id="email"
            v-model="email"
            name="email"
            type="email"
            autocomplete="username"
            maxlength="254"
            required
          />
          <label class="field-label" for="password">Password</label>
          <div class="password-field">
            <input
              id="password"
              v-model="password"
              name="password"
              :type="passwordVisible ? 'text' : 'password'"
              autocomplete="current-password"
              maxlength="256"
              required
            />
            <button
              type="button"
              class="password-toggle"
              :aria-label="passwordVisible ? 'Hide password' : 'Show password'"
              @click="passwordVisible = !passwordVisible"
            >
              {{ passwordVisible ? "Hide" : "Show" }}
            </button>
          </div>
          <label class="checkbox-field"
            ><input v-model="remember" type="checkbox" />
            <span>Keep me signed in on this device</span></label
          >
          <button
            class="primary-button sign-in-submit"
            type="submit"
            :disabled="!valid || submitting"
          >
            {{ submitting ? "Signing in…" : "Sign in" }}
          </button>
        </template>
        <a
          v-else
          class="primary-button sign-in-submit enterprise-sign-in"
          href="/api/v1/auth/oidc/start"
        >Continue with enterprise sign-in</a>
        <p class="sign-in-help">
          {{
            oidcEnabled
              ? "Access is limited to pre-authorized organizational accounts."
              : "Development accounts use fictional data only. Production identity providers are not configured locally."
          }}
        </p>
      </form>
    </section>
  </main>
</template>
