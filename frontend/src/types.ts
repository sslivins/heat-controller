export interface Tag {
  id: number;
  key: string;
  value: string;
}

export type ValidationStatus = "PENDING" | "REACHABLE" | "UNREACHABLE" | "AUTH_FAILED";

export interface Device {
  id: number;
  name: string;
  site: string;
  host: string;
  port: number;
  use_https: boolean;
  verify_tls: boolean;
  username: string | null;
  enabled: boolean;
  validation_status: ValidationStatus;
  last_validation_error: string | null;
  last_validated_at: string | null;
  created_at: string;
  updated_at: string;
  tags: Tag[];
}

export interface DeviceCreate {
  name: string;
  site: string;
  host: string;
  port?: number;
  use_https?: boolean;
  verify_tls?: boolean;
  username?: string | null;
  password?: string | null;
  enabled?: boolean;
  tag_ids?: number[];
}

export interface DeviceUpdate {
  name?: string;
  site?: string;
  host?: string;
  port?: number;
  use_https?: boolean;
  verify_tls?: boolean;
  username?: string | null;
  password?: string | null;
  enabled?: boolean;
  tag_ids?: number[];
}

/** Cached status pushed live over /ws/status (and returned in the initial snapshot). */
export interface DeviceStatusMessage {
  device_id: number;
  state: "pending" | "online" | "degraded" | "offline";
  mode: string | null;
  thermostat_state: string | null;
  space_temp: number | null;
  heat_temp: number | null;
  cool_temp: number | null;
  consecutive_failures: number;
  last_success_at: string | null;
  last_error: string | null;
  last_error_at: string | null;
  updated_at: string;
}

export type WsMessage =
  | { type: "snapshot"; devices: DeviceStatusMessage[] }
  | ({ type: "device_status" } & DeviceStatusMessage);

export type BulkOutcome = "applied" | "rejected" | "unreachable" | "timed_out" | "skipped_disabled";

export interface BulkApplyRequest {
  device_ids: number[];
  mode?: string | null;
  heat_temp?: number | null;
  cool_temp?: number | null;
}

export interface BulkApplyResult {
  device_id: number;
  outcome: BulkOutcome;
  error: string | null;
}

export interface BulkApplyResponse {
  results: BulkApplyResult[];
}
