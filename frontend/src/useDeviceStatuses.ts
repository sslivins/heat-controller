import { useEffect, useRef, useState } from "react";
import { wsStatusUrl } from "./api";
import type { DeviceStatusMessage, WsMessage } from "./types";

/**
 * Maintains a map of device_id -> latest status, fed by /ws/status.
 * Reconnects with backoff on drop (dev-server restarts, network blips)
 * so the dashboard doesn't need a page refresh to recover live status.
 */
export function useDeviceStatuses(): Map<number, DeviceStatusMessage> {
  const [statuses, setStatuses] = useState<Map<number, DeviceStatusMessage>>(new Map());
  const retryDelayRef = useRef(1000);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;

    function connect() {
      if (cancelled) return;
      socket = new WebSocket(wsStatusUrl());

      socket.onopen = () => {
        retryDelayRef.current = 1000;
      };

      socket.onmessage = (event) => {
        const msg = JSON.parse(event.data) as WsMessage;
        if (msg.type === "snapshot") {
          setStatuses(new Map(msg.devices.map((d) => [d.device_id, d])));
        } else if (msg.type === "device_status") {
          setStatuses((prev) => {
            const next = new Map(prev);
            next.set(msg.device_id, msg);
            return next;
          });
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        retryTimer = setTimeout(connect, retryDelayRef.current);
        retryDelayRef.current = Math.min(retryDelayRef.current * 2, 15000);
      };

      socket.onerror = () => {
        socket?.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  return statuses;
}
