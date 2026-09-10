import { useEffect, useRef } from "react";
import { useAuthStore } from "../store/authStore";

/**
 * Subscribe to the backend WebSocket for real-time alerts.
 * Calls onAlert for each new alert pushed. Falls back to polling silently.
 */
export function useRealtimeAlerts(onAlert: (a: any) => void) {
  const token = useAuthStore((s) => s.token);
  const cbRef = useRef(onAlert);
  cbRef.current = onAlert;

  useEffect(() => {
    if (!token) return;
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const base = import.meta.env.VITE_WS_URL || `${proto}//${window.location.host}`;
    let ws: WebSocket | null = null;
    let retry = 0;
    let closed = false;

    const connect = () => {
      try {
        ws = new WebSocket(
          `${base}/ws/alerts?token=${encodeURIComponent(token)}`
        );
      } catch {
        return;
      }
      ws.onopen = () => {
        retry = 0;
        ws?.send("ping");
      };
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === "alert.new") cbRef.current(data.alert);
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        if (!closed && retry < 5) {
          retry += 1;
          setTimeout(connect, 5000 * retry);
        }
      };
      ws.onerror = () => ws?.close();
    };

    connect();
    const ping = setInterval(() => {
      try {
        ws?.send("ping");
      } catch {
        /* socket not open */
      }
    }, 30000);

    return () => {
      closed = true;
      clearInterval(ping);
      ws?.close();
    };
  }, [token]);
}