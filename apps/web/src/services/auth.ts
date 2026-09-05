import { reactive } from "vue";
import type { Session, User } from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export const authState = reactive<{
  session: Session | null;
  initialized: boolean;
}>({ session: null, initialized: false });

let initialization: Promise<void> | null = null;

export function setSession(session: Session): void {
  authState.session = session;
  authState.initialized = true;
}

export function clearSession(): void {
  authState.session = null;
  authState.initialized = true;
}

export async function initializeSession(): Promise<void> {
  if (authState.initialized) return;
  if (!initialization) {
    initialization = fetch(`${API_BASE}/api/v1/auth/session`, {
      credentials: "include",
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (!response.ok) return;
        const user = (await response.json()) as User;
        authState.session = { user };
      })
      .finally(() => {
        authState.initialized = true;
      });
  }
  await initialization;
}

export async function signOut(): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/json" },
    });
  } finally {
    clearSession();
  }
}

export function hasRole(...roles: string[]): boolean {
  return Boolean(
    authState.session?.user.roles.some((role) => roles.includes(role)),
  );
}
