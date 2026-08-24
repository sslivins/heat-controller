import type { Device, DeviceStatusMessage } from "./types";
import { StatusBadge } from "./StatusBadge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

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
          <div className="grid grid-cols-4 gap-2 rounded-md bg-muted/50 p-2 text-center text-xs">
            <div>
              <div className="text-muted-foreground">Mode</div>
              <div className="font-medium">{status.mode ?? "—"}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Space</div>
              <div className="font-medium">{status.space_temp ?? "—"}&deg;</div>
            </div>
            <div>
              <div className="text-muted-foreground">Heat</div>
              <div className="font-medium">{status.heat_temp ?? "—"}&deg;</div>
            </div>
            <div>
              <div className="text-muted-foreground">Cool</div>
              <div className="font-medium">{status.cool_temp ?? "—"}&deg;</div>
            </div>
          </div>
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
