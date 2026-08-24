import type { DeviceStatusMessage } from "./types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const LABELS: Record<DeviceStatusMessage["state"], string> = {
  pending: "Pending",
  online: "Online",
  degraded: "Degraded",
  offline: "Offline",
};

const CLASSES: Record<DeviceStatusMessage["state"], string> = {
  pending: "bg-muted text-muted-foreground",
  online: "bg-success/15 text-success border-success/30",
  degraded: "bg-warning/15 text-warning border-warning/30",
  offline: "bg-destructive/15 text-destructive border-destructive/30",
};

export function StatusBadge({ status }: { status: DeviceStatusMessage | undefined }) {
  const state = status?.state ?? "pending";
  return (
    <Badge variant="outline" className={cn("font-medium", CLASSES[state])}>
      <span
        className={cn("mr-1.5 size-1.5 rounded-full", {
          "bg-muted-foreground": state === "pending",
          "bg-success": state === "online",
          "bg-warning": state === "degraded",
          "bg-destructive": state === "offline",
        })}
      />
      {LABELS[state]}
    </Badge>
  );
}
