import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { useDeviceStatuses } from "./useDeviceStatuses";
import { DeviceCard } from "./DeviceCard";
import { BulkActionBar } from "./BulkActionBar";
import { DeviceForm } from "./DeviceForm";
import type { Device, DeviceCreate, DeviceUpdate, Tag } from "./types";
import "./App.css";

export default function App() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [editingDevice, setEditingDevice] = useState<Device | null | undefined>(undefined); // undefined = form closed
  const statuses = useDeviceStatuses();

  async function refresh() {
    const [d, t] = await Promise.all([api.listDevices(), api.listTags()]);
    setDevices(d);
    setTags(t);
  }

  useEffect(() => {
    refresh()
      .catch((err) => setLoadError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, []);

  const groupedBySite = useMemo(() => {
    const groups = new Map<string, Device[]>();
    for (const d of devices) {
      const list = groups.get(d.site) ?? [];
      list.push(d);
      groups.set(d.site, list);
    }
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [devices]);

  function toggleSelect(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleBulkApply(mode: string | null, heatTemp: number | null, coolTemp: number | null) {
    return api.bulkApply({ device_ids: [...selected], mode, heat_temp: heatTemp, cool_temp: coolTemp });
  }

  async function handleSaveDevice(payload: DeviceCreate | DeviceUpdate) {
    if (editingDevice) {
      await api.updateDevice(editingDevice.id, payload);
    } else {
      await api.createDevice(payload as DeviceCreate);
    }
    await refresh();
  }

  async function handleDeleteDevice(device: Device) {
    if (!confirm(`Delete "${device.name}"? This cannot be undone.`)) return;
    await api.deleteDevice(device.id);
    setSelected((prev) => {
      const next = new Set(prev);
      next.delete(device.id);
      return next;
    });
    await refresh();
  }

  if (loading) return <div className="app-loading">Loading…</div>;
  if (loadError) return <div className="app-error">Failed to load: {loadError}</div>;

  return (
    <div className="app">
      <header className="app__header">
        <h1>heat-controller</h1>
        <button type="button" onClick={() => setEditingDevice(null)}>
          + Add device
        </button>
      </header>

      {devices.length === 0 ? (
        <div className="empty-state">No devices yet. Add one to get started.</div>
      ) : (
        groupedBySite.map(([site, siteDevices]) => (
          <section key={site} className="site-group">
            <h2>{site}</h2>
            <div className="device-grid">
              {siteDevices.map((device) => (
                <DeviceCard
                  key={device.id}
                  device={device}
                  status={statuses.get(device.id)}
                  selected={selected.has(device.id)}
                  onToggleSelect={toggleSelect}
                  onEdit={setEditingDevice}
                  onDelete={handleDeleteDevice}
                />
              ))}
            </div>
          </section>
        ))
      )}

      <BulkActionBar
        selectedCount={selected.size}
        onClear={() => setSelected(new Set())}
        onApply={handleBulkApply}
      />

      {editingDevice !== undefined && (
        <DeviceForm
          device={editingDevice}
          tags={tags}
          onSave={handleSaveDevice}
          onClose={() => setEditingDevice(undefined)}
        />
      )}
    </div>
  );
}
