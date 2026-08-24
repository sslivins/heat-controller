import { useEffect, useState } from "react";
import type { Device, DeviceStatusMessage } from "./types";
import { StatusBadge } from "./StatusBadge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { Droplets, Flame, Minus, Plus, Snowflake, Power, Wind } from "lucide-react";

interface Props {
  device: Device;
  status: DeviceStatusMessage | undefined;
  selected: boolean;
  onToggleSelect: (id: number) => void;
  onEdit: (device: Device) => void;
  onDelete: (device: Device) => void;
  onApply: (
    deviceId: number,
    mode: string | null,
    heatTemp: number | null,
    coolTemp: number | null,
  ) => Promise<void>;
}

const MODES = ["OFF", "HEAT", "COOL", "AUTO"] as const;

// Mode-specific color accents, consistent with the thermostat-UX convention
// (orange/red = heat, blue = cool) so the active mode is unmistakable even
// before reading any text -- see session research on Nest/Ecobee card design.
const MODE_ACCENT: Record<string, string> = {
  HEAT: "text-orange-500 dark:text-orange-400",
  COOL: "text-sky-500 dark:text-sky-400",
  AUTO: "text-violet-500 dark:text-violet-400",
  OFF: "text-muted-foreground",
};

const MODE_ICON: Record<string, typeof Flame> = {
  HEAT: Flame,
  COOL: Snowflake,
  AUTO: Wind,
  OFF: Power,
};

export function DeviceCard({ device, status, selected, onToggleSelect, onEdit, onDelete, onApply }: Props) {
  const mode = status?.mode ?? null;
  const accent = MODE_ACCENT[mode ?? "OFF"] ?? MODE_ACCENT.OFF;
  const ModeIcon = MODE_ICON[mode ?? "OFF"] ?? Power;

  // The setpoint shown/edited depends on the current mode: a HEAT-mode
  // thermostat only exposes its heat setpoint on the physical unit, not a
  // cool setpoint (and vice versa). AUTO shows both. OFF/unknown shows heat
  // as a fallback so the control isn't empty.
  const showCool = mode === "COOL" || mode === "AUTO";
  const showHeat = mode !== "COOL";

  const [heatDraft, setHeatDraft] = useState(status?.heat_temp ?? null);
  const [coolDraft, setCoolDraft] = useState(status?.cool_temp ?? null);
  const [busy, setBusy] = useState(false);

  // Keep local drafts in sync with live status pushes, but don't fight the
  // user mid-edit -- only resync while not busy applying a change.
  useEffect(() => {
    if (busy) return;
    setHeatDraft(status?.heat_temp ?? null);
    setCoolDraft(status?.cool_temp ?? null);
  }, [status?.heat_temp, status?.cool_temp, busy]);

  async function applyMode(nextMode: string) {
    setBusy(true);
    try {
      await onApply(device.id, nextMode, null, null);
    } finally {
      setBusy(false);
    }
  }

  async function applySetpoints(nextHeat: number | null, nextCool: number | null) {
    setBusy(true);
    try {
      await onApply(device.id, null, nextHeat, nextCool);
    } finally {
      setBusy(false);
    }
  }

  function step(which: "heat" | "cool", delta: number) {
    if (which === "heat") {
      const next = (heatDraft ?? 68) + delta;
      setHeatDraft(next);
      void applySetpoints(next, null);
    } else {
      const next = (coolDraft ?? 76) + delta;
      setCoolDraft(next);
      void applySetpoints(null, next);
    }
  }

  return (
    <Card
      className={cn(
        "gap-4 py-4 transition-colors",
        selected && "border-primary ring-2 ring-primary/20",
      )}
    >
      <CardHeader className="grid-cols-[auto_1fr_auto] items-center gap-3 px-4">
        <Checkbox
          checked={selected}
          onCheckedChange={() => onToggleSelect(device.id)}
          aria-label={`Select ${device.name}`}
        />
        <div className="flex flex-col overflow-hidden">
          <span className="truncate font-semibold leading-tight">{device.name}</span>
          <span className="truncate text-xs text-muted-foreground">{device.host}</span>
        </div>
        <StatusBadge status={status} />
      </CardHeader>

      <CardContent className="flex flex-col gap-3 px-4">
        {status ? (
          <>
            {/* Prominent current-conditions readout -- the thing you glance at first. */}
            <div className="flex items-center justify-between rounded-lg bg-muted/50 px-4 py-3">
              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-bold tabular-nums leading-none">
                  {status.space_temp ?? "—"}
                </span>
                <span className="text-lg font-semibold text-muted-foreground">&deg;</span>
              </div>
              <div className="flex flex-col items-end gap-1">
                <div className={cn("flex items-center gap-1 text-sm font-medium", accent)}>
                  <ModeIcon className="size-4" />
                  {mode ?? "Unknown"}
                </div>
                {status.humidity != null && (
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Droplets className="size-3.5" />
                    {status.humidity}% humidity
                  </div>
                )}
              </div>
            </div>

            {/* Mode-specific setpoint controls -- only the setpoint(s) relevant
                to the current mode are shown, per common thermostat UX (a
                HEAT-mode unit doesn't show a cool setpoint, and vice versa). */}
            <div className="grid grid-cols-2 gap-2">
              <Select value={mode ?? ""} onValueChange={applyMode} disabled={busy}>
                <SelectTrigger className="col-span-2 h-8 text-xs">
                  <SelectValue placeholder="Mode" />
                </SelectTrigger>
                <SelectContent>
                  {MODES.map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {showHeat && (
                <div className="flex items-center justify-between rounded-md border-2 bg-muted/40 px-2 py-1.5">
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase text-muted-foreground">Heat to</span>
                    <span className="font-semibold tabular-nums">{heatDraft ?? "—"}&deg;</span>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      type="button"
                      size="icon-xs"
                      variant="outline"
                      disabled={busy}
                      onClick={() => step("heat", -1)}
                      aria-label="Decrease heat setpoint"
                    >
                      <Minus />
                    </Button>
                    <Button
                      type="button"
                      size="icon-xs"
                      variant="outline"
                      disabled={busy}
                      onClick={() => step("heat", 1)}
                      aria-label="Increase heat setpoint"
                    >
                      <Plus />
                    </Button>
                  </div>
                </div>
              )}

              {showCool && (
                <div className="flex items-center justify-between rounded-md border-2 bg-muted/40 px-2 py-1.5">
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase text-muted-foreground">Cool to</span>
                    <span className="font-semibold tabular-nums">{coolDraft ?? "—"}&deg;</span>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      type="button"
                      size="icon-xs"
                      variant="outline"
                      disabled={busy}
                      onClick={() => step("cool", -1)}
                      aria-label="Decrease cool setpoint"
                    >
                      <Minus />
                    </Button>
                    <Button
                      type="button"
                      size="icon-xs"
                      variant="outline"
                      disabled={busy}
                      onClick={() => step("cool", 1)}
                      aria-label="Increase cool setpoint"
                    >
                      <Plus />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="rounded-md bg-muted/50 p-2 text-center text-xs text-muted-foreground">
            No status yet
          </div>
        )}

        {device.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {device.tags.map((t) => (
              <Badge key={t.id} variant="secondary" className="font-normal">
                {t.key}:{t.value}
              </Badge>
            ))}
          </div>
        )}

        {!device.enabled && (
          <Badge variant="outline" className="w-fit text-muted-foreground">
            Disabled
          </Badge>
        )}
        {status?.last_error && (
          <div className="rounded-md bg-destructive/10 px-2 py-1 text-xs text-destructive">
            {status.last_error}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" size="sm" variant="outline" onClick={() => onEdit(device)}>
            Edit
          </Button>
          <Button type="button" size="sm" variant="destructive" onClick={() => onDelete(device)}>
            Delete
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
