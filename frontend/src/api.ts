/** Thin fetch wrapper for the goodhvac API. Base URL comes from Vite env / dev proxy. */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail ?? detail;
    } catch {
      // response wasn't JSON; fall back to statusText
    }
    throw new Error(`${resp.status} ${detail}`);
  }

  if (resp.status === 204) {
    return undefined as T;
  }
  return (await resp.json()) as T;
}

import type {
  BulkApplyRequest,
  BulkApplyResponse,
  Device,
  DeviceCreate,
  DeviceUpdate,
  Tag,
} from "./types";

export const api = {
  listDevices: () => request<Device[]>("/devices"),
  createDevice: (payload: DeviceCreate) =>
    request<Device>("/devices", { method: "POST", body: JSON.stringify(payload) }),
  updateDevice: (id: number, payload: DeviceUpdate) =>
    request<Device>(`/devices/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteDevice: (id: number) => request<void>(`/devices/${id}`, { method: "DELETE" }),

  listTags: () => request<Tag[]>("/tags"),
  createTag: (key: string, value: string) =>
    request<Tag>("/tags", { method: "POST", body: JSON.stringify({ key, value }) }),
  deleteTag: (id: number) => request<void>(`/tags/${id}`, { method: "DELETE" }),

  bulkApply: (payload: BulkApplyRequest) =>
    request<BulkApplyResponse>("/devices/bulk-apply", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

/** Resolves the /ws/status URL relative to the API base (works for both dev proxy and prod). */
export function wsStatusUrl(): string {
  if (BASE_URL) {
    return BASE_URL.replace(/^http/, "ws") + "/ws/status";
  }
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/ws/status`;
}
