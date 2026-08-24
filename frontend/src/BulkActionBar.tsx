import { useState } from "react";
import type { BulkApplyResponse } from "./types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface Props {
  selectedCount: number;
  onClear: () => void;
  onApply: (mode: string | null, heatTemp: number | null, coolTemp: number | null) => Promise<BulkApplyResponse>;
}

const MODES = ["OFF", "HEAT", "COOL", "AUTO"] as const;

export function BulkActionBar({ selectedCount, onClear, onApply }: Props) {
  const [mode, setMode] = useState<string>("");
  const [heatTemp, setHeatTemp] = useState<string>("");
  const [coolTemp, setCoolTemp] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<BulkApplyResponse | null>(null);

  if (selectedCount === 0) return null;

  async function handleApply() {
    setBusy(true);
    setResult(null);
    try {
      const res = await onApply(
        mode || null,
        heatTemp ? Number(heatTemp) : null,
        coolTemp ? Number(coolTemp) : null,
      );
      setResult(res);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-10 border-t bg-card/95 shadow-lg backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="text-sm">
            <strong>{selectedCount}</strong> device{selectedCount === 1 ? "" : "s"} selected
            <Button type="button" variant="link" size="sm" className="ml-1 h-auto p-0" onClick={onClear}>
              Clear
            </Button>
          </div>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <Select value={mode || "unchanged"} onValueChange={(v) => setMode(v === "unchanged" ? "" : v)}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="Mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="unchanged">Mode: unchanged</SelectItem>
                {MODES.map((m) => (
                  <SelectItem key={m} value={m}>
                    {m}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              type="number"
              placeholder="Heat °"
              className="w-24"
              value={heatTemp}
              onChange={(e) => setHeatTemp(e.target.value)}
            />
            <Input
              type="number"
              placeholder="Cool °"
              className="w-24"
              value={coolTemp}
              onChange={(e) => setCoolTemp(e.target.value)}
            />
            <Button type="button" disabled={busy} onClick={handleApply}>
              {busy ? "Applying…" : "Apply"}
            </Button>
          </div>
        </div>

        {result && (
          <div className="flex flex-wrap gap-1.5">
            {result.results.map((r) => (
              <Badge
                key={r.device_id}
                variant="outline"
                className={cn(
                  r.outcome === "applied" && "border-success/30 bg-success/15 text-success",
                  r.outcome === "timed_out" && "border-warning/30 bg-warning/15 text-warning",
                  r.outcome !== "applied" && r.outcome !== "timed_out" && "border-destructive/30 bg-destructive/15 text-destructive",
                )}
              >
                #{r.device_id}: {r.outcome}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
