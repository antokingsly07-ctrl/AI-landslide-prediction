import { api } from "../lib/api";
import {
  getPendingReports,
  removePendingReport,
  updatePendingReport,
} from "../store/offlineDb";
import type { PendingReport } from "../store/offlineDb";

let syncing = false;

export function isOnline(): boolean {
  return typeof navigator !== "undefined" ? navigator.onLine : true;
}

export function generateClientId(): string {
  return `client_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export async function syncPendingReports(): Promise<{
  synced: number;
  failed: number;
}> {
  if (syncing) return { synced: 0, failed: 0 };
  if (!isOnline()) return { synced: 0, failed: 0 };

  syncing = true;
  let synced = 0;
  let failed = 0;
  try {
    const pending = await getPendingReports();
    const toSync = pending.filter((p) => p.sync_status === "pending_sync" || p.sync_status === "failed");
    if (toSync.length === 0) return { synced: 0, failed: 0 };

    const items = toSync.map((p) => ({
      client_id: p.client_id,
      report_type: p.report_type,
      severity: p.severity,
      description: p.description,
      latitude: p.latitude,
      longitude: p.longitude,
      device_location_manual: p.device_location_manual,
      photos: p.photos,
    }));

    const res = await api.post("/sync", items);
    const data = res.data as { synced: any[]; duplicates: string[] };
    const syncedIds = new Set([
      ...data.synced.map((s) => s.client_id),
      ...data.duplicates,
    ]);
    for (const item of toSync) {
      await removePendingReport(item.client_id);
      if (syncedIds.has(item.client_id)) synced++;
    }
  } catch (err) {
    // mark pending as failed, retry later
    const pending = await getPendingReports();
    for (const p of pending.filter((p) => p.sync_status === "pending_sync")) {
      p.sync_status = "failed";
      p.retry_count = (p.retry_count || 0) + 1;
      await updatePendingReport(p);
      failed++;
    }
  } finally {
    syncing = false;
  }
  return { synced, failed };
}

export function subscribeToOnline(cb: () => void): () => void {
  const onOnline = () => cb();
  window.addEventListener("online", onOnline);
  return () => window.removeEventListener("online", onOnline);
}
