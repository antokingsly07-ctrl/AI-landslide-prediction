import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import type { Road } from "../types";
import { roadStatusColor } from "../lib/utils";

export default function Roads() {
  const { t } = useTranslation();
  const [roads, setRoads] = useState<Road[]>([]);

  useEffect(() => {
    api.get("/roads").then((r) => setRoads(r.data)).catch(() => {});
  }, []);

  const updateStatus = async (id: string, status: string) => {
    try {
      await api.patch(`/roads/${id}/status`, { status });
      setRoads((r) => r.map((x) => (x.id === id ? { ...x, status } : x)));
    } catch {
      /* ignore */
    }
  };

  const blocked = roads.filter((r) => r.status === "blocked" || r.status === "severely_blocked").length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t("nav.roads")}</h2>
        <span className="badge bg-red-100 text-red-700">
          {blocked} blocked / {roads.length} total
        </span>
      </div>
      <div className="grid gap-3">
        {roads.map((r) => (
          <div key={r.id} className="card flex items-center justify-between gap-4">
            <div>
              <div className="font-semibold">{r.name}</div>
              <div className="text-xs text-slate-500 capitalize">{r.road_type}</div>
              <div className="text-xs text-slate-500 mt-1">
                Pop served: {r.population_served} · Alternative: {r.alternative_route ? "Yes" : "No"} · Priority{" "}
                {r.priority_score}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`badge ${roadStatusColor(r.status)} capitalize`}>{r.status}</span>
              <select
                className="input !w-auto !py-1 text-sm"
                value={r.status}
                onChange={(e) => updateStatus(r.id, e.target.value)}
              >
                {["open", "restricted", "blocked", "unknown"].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ))}
        {roads.length === 0 && (
          <div className="card text-center text-slate-500 py-10">No roads</div>
        )}
      </div>
    </div>
  );
}
