import type { Device, DeviceStatusMessage } from "./types";
import { StatusBadge } from "./StatusBadge";

interface Props {
  device: Device;
  status: DeviceStatusMessage | undefined;
  selected: boolean;
  onToggleSelect: (id: number) => void;
  onEdit: (device: Device) => void;
  onDelete: (device: Device) => void;
}

export function DeviceCard({ device, status, selected, onToggleSelect, onEdit, onDelete }: Props) {
  return (
    <div className={`device-card ${selected ? "device-card--selected" : ""}`}>
      <div className="device-card__header">
        <label className="device-card__select">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggleSelect(device.id)}
            aria-label={`Select ${device.name}`}
          />
        </label>
        <div className="device-card__title">
          <strong>{device.name}</strong>
          <span className="device-card__host">{device.host}</span>
        </div>
        <StatusBadge status={status} />
      </div>

      <div className="device-card__body">
        {status ? (
          <div className="device-card__readings">
            <span>Mode: {status.mode ?? "—"}</span>
            <span>Space: {status.space_temp ?? "—"}&deg;</span>
            <span>Heat: {status.heat_temp ?? "—"}&deg;</span>
            <span>Cool: {status.cool_temp ?? "—"}&deg;</span>
          </div>
        ) : (
          <div className="device-card__readings device-card__readings--empty">No status yet</div>
        )}

        {device.tags.length > 0 && (
          <div className="device-card__tags">
            {device.tags.map((t) => (
              <span key={t.id} className="tag-pill">
                {t.key}:{t.value}
              </span>
            ))}
          </div>
        )}

        {!device.enabled && <div className="device-card__disabled">Disabled</div>}
        {status?.last_error && <div className="device-card__error">{status.last_error}</div>}
      </div>

      <div className="device-card__actions">
        <button type="button" onClick={() => onEdit(device)}>
          Edit
        </button>
        <button type="button" className="button--danger" onClick={() => onDelete(device)}>
          Delete
        </button>
      </div>
    </div>
  );
}
