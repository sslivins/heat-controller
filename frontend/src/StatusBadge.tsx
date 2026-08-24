import type { DeviceStatusMessage } from "./types";

const LABELS: Record<DeviceStatusMessage["state"], string> = {
  pending: "Pending",
  online: "Online",
  degraded: "Degraded",
  offline: "Offline",
};

const COLORS: Record<DeviceStatusMessage["state"], string> = {
  pending: "#9aa0a6",
  online: "#1e8e3e",
  degraded: "#e37400",
  offline: "#c5221f",
};

export function StatusBadge({ status }: { status: DeviceStatusMessage | undefined }) {
  const state = status?.state ?? "pending";
  return (
    <span className="status-badge" style={{ backgroundColor: COLORS[state] }}>
      {LABELS[state]}
    </span>
  );
}
