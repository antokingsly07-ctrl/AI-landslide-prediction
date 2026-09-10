import { openDB } from "idb";
import type { DBSchema } from "idb";

export interface PendingReport {
  client_id: string;
  report_type: string;
  severity: string;
  description?: string;
  latitude: number;
  longitude: number;
  device_location_manual: boolean;
  reported_at: string;
  photos: string[]; // base64 data URLs
  sync_status: "pending_sync" | "synced" | "failed";
  retry_count: number;
}

interface LandslideDB extends DBSchema {
  pending_reports: {
    key: string;
    value: PendingReport;
  };
  cache: {
    key: string;
    value: { value: string };
  };
}

let _dbPromise: Promise<unknown> | null = null;

function getDB() {
  if (!_dbPromise) {
    _dbPromise = openDB<LandslideDB>("landslide-offline", 1, {
      upgrade(db) {
        db.createObjectStore("pending_reports", { keyPath: "client_id" });
        db.createObjectStore("cache");
      },
    });
  }
  return _dbPromise as Promise<any>;
}

export async function savePendingReport(report: PendingReport): Promise<void> {
  const db = await getDB();
  await db.put("pending_reports", report);
}

export async function getPendingReports(): Promise<PendingReport[]> {
  const db = await getDB();
  return (await db.getAll("pending_reports")) as PendingReport[];
}

export async function updatePendingReport(report: PendingReport): Promise<void> {
  const db = await getDB();
  await db.put("pending_reports", report);
}

export async function removePendingReport(client_id: string): Promise<void> {
  const db = await getDB();
  await db.delete("pending_reports", client_id);
}

export async function setCache(key: string, value: string): Promise<void> {
  const db = await getDB();
  await db.put("cache", { value }, key);
}

export async function getCache(key: string): Promise<string | undefined> {
  const db = await getDB();
  const row = await db.get("cache", key);
  return row?.value;
}

export async function clearCache(): Promise<void> {
  const db = await getDB();
  (await db.getAllKeys("cache")).forEach(async (k: any) => db.delete("cache", k));
}
