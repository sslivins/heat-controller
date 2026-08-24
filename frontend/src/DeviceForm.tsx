import { useState } from "react";
import type { Device, DeviceCreate, DeviceUpdate, Tag } from "./types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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
  const [pin, setPin] = useState("");
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
      if (pin) {
        payload.pin = pin;
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
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>{device ? "Edit device" : "Add device"}</DialogTitle>
          </DialogHeader>

          <div className="grid gap-1.5">
            <Label htmlFor="name">Name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="site">Site</Label>
            <Input id="site" value={site} onChange={(e) => setSite(e.target.value)} required />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="host">Host</Label>
            <Input id="host" value={host} onChange={(e) => setHost(e.target.value)} required />
          </div>

          <div className="flex flex-wrap items-end gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="port">Port</Label>
              <Input
                id="port"
                type="number"
                className="w-24"
                value={port}
                onChange={(e) => setPort(e.target.value)}
              />
            </div>
            <label className="flex items-center gap-2 pb-2 text-sm">
              <Checkbox checked={useHttps} onCheckedChange={(v) => setUseHttps(v === true)} />
              HTTPS
            </label>
            <label className="flex items-center gap-2 pb-2 text-sm">
              <Checkbox checked={verifyTls} onCheckedChange={(v) => setVerifyTls(v === true)} />
              Verify TLS
            </label>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="username">Username</Label>
            <Input id="username" value={username} onChange={(e) => setUsername(e.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="password">
              Password
              {device && <span className="ml-1 text-xs text-muted-foreground">(leave blank to keep current)</span>}
            </Label>
            <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="pin">
              Lockout PIN
              <span className="ml-1 text-xs text-muted-foreground">
                {device
                  ? device.has_pin
                    ? "(configured — leave blank to keep current)"
                    : "(optional — leave blank if none set on the thermostat)"
                  : "(optional — only if a PIN is set on the thermostat's touchscreen)"}
              </span>
            </Label>
            <Input
              id="pin"
              type="password"
              inputMode="numeric"
              maxLength={4}
              value={pin}
              onChange={(e) => setPin(e.target.value)}
            />
          </div>

          <label className="flex items-center gap-2 text-sm">
            <Checkbox checked={enabled} onCheckedChange={(v) => setEnabled(v === true)} />
            Enabled
          </label>

          {tags.length > 0 && (
            <div className="grid gap-1.5">
              <Label>Tags</Label>
              <div className="flex flex-wrap gap-1.5">
                {tags.map((t) => {
                  const active = tagIds.includes(t.id);
                  return (
                    <Badge
                      key={t.id}
                      variant={active ? "default" : "outline"}
                      className="cursor-pointer select-none font-normal"
                      onClick={() => toggleTag(t.id)}
                    >
                      {t.key}:{t.value}
                    </Badge>
                  );
                })}
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
