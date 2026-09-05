import { authState, clearSession } from "@/services/auth";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly correlationId?: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (authState.session?.access_token)
    headers.set("Authorization", `Bearer ${authState.session.access_token}`);
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    if (response.status === 401) clearSession();
    const problem = (await response.json().catch(() => ({}))) as {
      detail?: string;
      correlation_id?: string;
    };
    throw new ApiError(
      problem.detail ?? `Request failed with status ${response.status}`,
      response.status,
      problem.correlation_id,
    );
  }
  return (await response.json()) as T;
}

export function uploadDocument<T>(
  claimId: string,
  file: File,
  onProgress: (percent: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${API_BASE}/api/v1/claims/${claimId}/documents`);
    request.withCredentials = true;
    if (authState.session?.access_token)
      request.setRequestHeader(
        "Authorization",
        `Bearer ${authState.session.access_token}`,
      );
    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable)
        onProgress(Math.round((event.loaded / event.total) * 100));
    });
    request.addEventListener("load", () => {
      const payload = JSON.parse(request.responseText || "{}") as T & {
        detail?: string;
        correlation_id?: string;
      };
      if (request.status >= 200 && request.status < 300) resolve(payload);
      else
        reject(
          new ApiError(
            payload.detail ?? `Upload failed with status ${request.status}`,
            request.status,
            payload.correlation_id,
          ),
        );
    });
    request.addEventListener("error", () =>
      reject(new ApiError("The upload connection failed", 0)),
    );
    const form = new FormData();
    form.append("file", file);
    request.send(form);
  });
}

export async function documentOriginal(path: string): Promise<Blob> {
  const headers = new Headers();
  if (authState.session?.access_token)
    headers.set("Authorization", `Bearer ${authState.session.access_token}`);
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    headers,
    credentials: "include",
  });
  if (!response.ok)
    throw new ApiError(
      `Original document is unavailable (${response.status})`,
      response.status,
    );
  return response.blob();
}
