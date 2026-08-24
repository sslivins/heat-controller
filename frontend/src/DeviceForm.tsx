import { useState } from "react";
import type { Device, DeviceCreate, DeviceUpdate, Tag } from "./types";

interface Props {
  device: Device | null; // null = creating a new device
  tags: Tag[];
  onSave: (payload: DeviceCreate | DeviceUpdate) => Promise<void>;
  onClose: () => void;
}

export function DeviceForm({ device, tags, onSave, onClose }: Props) {
  const [name, setName] = useState(device?.name ?? "");
  const [site, setSite] = useState(device?.site ?? "");
  const [host, setHost] = useState(device?.host ?? "");
  const [port, setPort] = useState(String(device?.port ?? 443));
  const [useHttps, setUseHttps] = useState(device?.use_https ?? true);
  const [verifyTls, setVerifyTls] = useState(device?.verify_tls ?? false);
  const [username, setUsername] = useState(device?.username ?? "");
  const [password, setPassword] = useState("");
  const [enabled, setEnabled] = useState(device?.enabled ?? true);
  const [tagIds, setTagIds] = useState<number[]>(device?.tags.map((t) => t.id) ?? []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleTag(id: number) {
    setTagIds((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload: DeviceCreate | DeviceUpdate = {
        name,
        site,
        host,
        port: Number(port),
        use_https: useHttps,
        verify_tls: verifyTls,
        username: username || null,
        enabled,
        tag_ids: tagIds,
      };
      if (password) {
        payload.password = password;
      }
      await onSave(payload);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2>{device ? "Edit device" : "Add device"}</h2>

        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Site
          <input value={site} onChange={(e) => setSite(e.target.value)} required />
        </label>
        <label>
          Host
          <input value={host} onChange={(e) => setHost(e.target.value)} required />
        </label>
        <div className="form-row">
          <label>
            Port
            <input type="number" value={port} onChange={(e) => setPort(e.target.value)} />
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={useHttps} onChange={(e) => setUseHttps(e.target.checked)} />
            HTTPS
          </label>
          <label className="checkbox-label">
            <input type="checkbox" checked={verifyTls} onChange={(e) => setVerifyTls(e.target.checked)} />
            Verify TLS
          </label>
        </div>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label>
          Password {device && <span className="hint">(leave blank to keep current)</span>}
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <label className="checkbox-label">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          Enabled
        </label>

        {tags.length > 0 && (
          <fieldset>
            <legend>Tags</legend>
            <div className="tag-picker">
              {tags.map((t) => (
                <label key={t.id} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={tagIds.includes(t.id)}
                    onChange={() => toggleTag(t.id)}
                  />
                  {t.key}:{t.value}
                </label>
              ))}
            </div>
          </fieldset>
        )}

        {error && <div className="form-error">{error}</div>}

        <div className="modal__actions">
          <button type="button" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}
