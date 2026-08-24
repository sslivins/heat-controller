import { useState } from "react";
import type { BulkApplyResponse } from "./types";

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
    <div className="bulk-bar">
      <div className="bulk-bar__summary">
        <strong>{selectedCount}</strong> device{selectedCount === 1 ? "" : "s"} selected
        <button type="button" onClick={onClear} className="link-button">
          Clear
        </button>
      </div>

      <div className="bulk-bar__controls">
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="">Mode: unchanged</option>
          {MODES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <input
          type="number"
          placeholder="Heat °"
          value={heatTemp}
          onChange={(e) => setHeatTemp(e.target.value)}
        />
        <input
          type="number"
          placeholder="Cool °"
          value={coolTemp}
          onChange={(e) => setCoolTemp(e.target.value)}
        />
        <button type="button" disabled={busy} onClick={handleApply}>
          {busy ? "Applying…" : "Apply"}
        </button>
      </div>

      {result && (
        <div className="bulk-bar__results">
          {result.results.map((r) => (
            <span key={r.device_id} className={`bulk-result bulk-result--${r.outcome}`}>
              #{r.device_id}: {r.outcome}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
