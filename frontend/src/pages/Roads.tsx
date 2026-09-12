import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import type { Road } from "../types";
import { roadPredictionLevelColor, roadStatusColor } from "../lib/utils";

interface PredictedRoad {
  id: string;
  name: string;
  status: string;
  district_name?: string;
  prediction_score: number;
  prediction_level: string;
  factors: { zone_risk_score: number; rain_24h_mm: number; nearby_incidents: number };
}

export default function Roads() {
  const { t } = useTranslation();
  const [roads, setRoads] = useState<Road[]>([]);
  const [predicted, setPredicted] = useState<PredictedRoad[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", road_type: "state", population_served: "0" });

  const load = () => {
    api.get("/roads").then((r) => setRoads(r.data)).catch(() => {});
    api.get("/roads/predicted-blocked").then((r) => setPredicted(r.data)).catch(() => {});
  };
  useEffect(load, []);

  const updateStatus = async (id: string, status: string) => {
    try {
      await api.patch(`/roads/${id}/status`, { status });
      setRoads((r) => r.map((x) => (x.id === id ? { ...x, status } : x)));
    } catch {
      /* ignore */
    }
  };

  const addRoad = async () => {
    if (!form.name.trim()) return;
    try {
      await api.post("/roads", {
        name: form.name,
        road_type: form.road_type,
        population_served: parseInt(form.population_served) || 0,
        alternative_route: true,
      });
      setForm({ name: "", road_type: "state", population_served: "0" });
      setShowAdd(false);
      load();
    } catch {
      /* ignore */
    }
  };

  const blocked = roads.filter((r) => r.status === "blocked" || r.status === "severely_blocked").length;
  const atRisk = roads.filter((r) => r.prediction_level === "high" || r.prediction_level === "critical").length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t("nav.roads")}</h2>
        <div className="flex items-center gap-2">
          {atRisk > 0 && (
            <span className="badge bg-orange-100 text-orange-700">
              {atRisk} predicted at-risk
            </span>
          )}
          <span className="badge bg-red-100 text-red-700">
            {blocked} blocked / {roads.length} total
          </span>
          <button className="btn btn-primary !py-1.5 text-sm" onClick={() => setShowAdd((v) => !v)}>
            + Add road
          </button>
        </div>
      </div>

      {showAdd && (
        <div className="card space-y-2">
          <div className="font-semibold text-sm">Register a road (Meghalaya)</div>
          <div className="flex flex-wrap gap-2">
            <input
              className="input !w-72 text-sm"
              placeholder="Road name, e.g. NH-6 Shillong-Silchar (section)"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
            <select
              className="input !w-auto text-sm"
              value={form.road_type}
              onChange={(e) => setForm({ ...form, road_type: e.target.value })}
            >
              {["highway", "state", "district", "village"].map((x) => (
                <option key={x} value={x}>{x}</option>
              ))}
            </select>
            <input
              className="input !w-28 text-sm"
              placeholder="Pop served"
              type="number"
              value={form.population_served}
              onChange={(e) => setForm({ ...form, population_served: e.target.value })}
            />
            <button className="btn btn-primary !py-1.5 text-sm" onClick={addRoad}>
              Register
            </button>
          </div>
        </div>
      )}

      {predicted.length > 0 && (
        <div className="card space-y-2">
          <div className="font-semibold text-sm">Possible landslide-blocked roads (prediction)</div>
          <div className="grid gap-2 sm:grid-cols-2">
            {predicted.map((p) => (
              <div key={p.id} className="rounded border border-slate-200 p-2 flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">{p.name}</div>
                  <div className="text-xs text-slate-500">
                    zone {p.factors.zone_risk_score.toFixed(0)} · rain {p.factors.rain_24h_mm.toFixed(0)} mm/24h ·{" "}
                    {p.factors.nearby_incidents} slide events near
                  </div>
                </div>
                <div className="text-right">
                  <div className={`badge ${roadPredictionLevelColor(p.prediction_level)} capitalize`}>
                    {p.prediction_level} {p.prediction_score.toFixed(0)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-3">
        {roads.map((r) => (
          <div key={r.id} className="card flex items-center justify-between gap-4">
            <div>
              <div className="font-semibold">{r.name}</div>
              <div className="text-xs text-slate-500 capitalize">
                {r.road_type} · {r.district_name || "Meghalaya"}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Pop served: {r.population_served} · Alternative: {r.alternative_route ? "Yes" : "No"} · Priority{" "}
                {r.priority_score}
                {r.prediction_score !== undefined && r.prediction_score > 0 && (
                  <span className="ml-2">
                    · Predicted blockage{" "}
                    <span className={`badge ${roadPredictionLevelColor(r.prediction_level)} capitalize`}>
                      {r.prediction_level} {r.prediction_score.toFixed(0)}%
                    </span>
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className={`badge ${roadStatusColor(r.status)} capitalize`}>{r.status}</span>
              <select
                className="input !w-auto !py-1 text-sm"
                value={r.status}
                onChange={(e) => updateStatus(r.id, e.target.value)}
              >
                {["open", "restricted", "blocked", "severely_blocked", "unknown"].map((s) => (
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