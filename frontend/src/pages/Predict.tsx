import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  MapContainer,
  TileLayer,
  Marker,
  useMapEvents,
  Popup,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api } from "../lib/api";
import { riskColor } from "../lib/utils";
import type { PredictionResponse } from "../types";

const NE_CENTER: [number, number] = [26.2, 93.0];

function ClickMarker({
  onPick,
  pos,
}: {
  onPick: (lat: number, lng: number) => void;
  pos: [number, number] | null;
}) {
  useMapEvents({
    click(e) {
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  if (!pos) return null;
  const icon = L.divIcon({
    className: "",
    html: `<div style="width:16px;height:16px;background:#7c3aed;border-radius:50%;border:3px solid white;box-shadow:0 0 8px rgba(124,58,237,.8)"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
  return (
    <Marker position={pos} icon={icon}>
      <Popup>Selected location</Popup>
    </Marker>
  );
}

export default function Predict() {
  const { t } = useTranslation();
  const [lat, setLat] = useState<number>(26.2);
  const [lng, setLng] = useState<number>(93.0);
  const [form, setForm] = useState({
    rainfall_24h: 120,
    rainfall_6h: 45,
    rainfall_1h: 12,
    rain_3d: 200,
    rain_7d: 320,
    soil_moisture: 60,
    slope_deg: 24,
    elevation_m: 700,
    historical_frequency: 2,
    distance_to_roads_m: 250,
    vegetation_change: 0.02,
    deformation_mm: 6,
  });
  const [result, setResult] = useState<PredictionResponse | null>(null);
  const [forecast, setForecast] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [autoFill, setAutoFill] = useState(false);

  useEffect(() => {
    if (autoFill) {
      api
        .get("/weather", { params: { lat, lon: lng } })
        .then((r: any) => {
          const d = r.data || {};
          setForm((f) => ({
            ...f,
            rainfall_24h: d.rain_24h ?? d.rainfall_24h ?? f.rainfall_24h,
            rainfall_6h: d.rain_6h ?? d.rainfall_6h ?? f.rainfall_6h,
            rainfall_1h: d.rain_1h ?? d.rainfall_1h ?? f.rainfall_1h,
            soil_moisture: d.soil_moisture ?? f.soil_moisture,
          }));
        })
        .catch(() => {});
      api
        .get("/ml/forecast", { params: { days: 7 } })
        .then((r) => setForecast(r.data))
        .catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoFill]);

  const set = (k: keyof typeof form, v: string) =>
    setForm((f) => ({ ...f, [k]: parseFloat(v) || 0 }));

  const runPrediction = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const r = await api.post("/predictions", { ...form, latitude: lat, longitude: lng });
      setResult(r.data);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Prediction failed");
    } finally {
      setLoading(false);
    }
  };

  const n = (v: number) =>
    v == null || isNaN(v) ? "—" : v.toFixed(1);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">AI Risk Prediction</h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card space-y-3">
          <div>
            <h3 className="font-semibold text-sm mb-1">1. Pick location on map</h3>
            <div className="flex gap-2 text-sm text-slate-600">
              <span>Lat:</span>
              <input
                type="number"
                step="0.0001"
                value={lat}
                onChange={(e) => setLat(parseFloat(e.target.value) || 0)}
                className="input !py-1 !px-2 w-32"
              />
              <span>Lng:</span>
              <input
                type="number"
                step="0.0001"
                value={lng}
                onChange={(e) => setLng(parseFloat(e.target.value) || 0)}
                className="input !py-1 !px-2 w-32"
              />
            </div>
          </div>
          <div className="h-72 rounded-lg overflow-hidden border border-slate-200">
            <MapContainer center={NE_CENTER} zoom={6} style={{ height: "100%", width: "100%" }}>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <ClickMarker onPick={(a, b) => { setLat(a); setLng(b); }} pos={[lat, lng]} />
            </MapContainer>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input type="checkbox" checked={autoFill} onChange={(e) => setAutoFill(e.target.checked)} className="accent-blue-600" />
            Auto-fill from live weather + 7-day forecast
          </label>

          <h3 className="font-semibold text-sm mt-2">2. Environmental features</h3>
          <div className="grid grid-cols-2 gap-3">
            {(
              [
                ["rainfall_24h", "Rainfall 24h (mm)"],
                ["rainfall_6h", "Rainfall 6h (mm)"],
                ["rainfall_1h", "Rainfall 1h (mm)"],
                ["rain_3d", "Rain 3-day (mm)"],
                ["rain_7d", "Rain 7-day (mm)"],
                ["soil_moisture", "Soil moisture (%)"],
                ["slope_deg", "Slope (deg)"],
                ["elevation_m", "Elevation (m)"],
                ["historical_frequency", "Historical landslides"],
                ["distance_to_roads_m", "Distance to road (m)"],
                ["vegetation_change", "Vegetation change"],
                ["deformation_mm", "Deformation (mm)"],
              ] as [keyof typeof form, string][]
            ).map(([key, label]) => (
              <label key={key} className="block text-xs text-slate-600">
                {label}
                <input
                  type="number"
                  step="any"
                  value={form[key]}
                  onChange={(e) => set(key, e.target.value)}
                  className="input !py-1.5 !px-2 mt-1 w-full"
                />
              </label>
            ))}
          </div>

          <button onClick={runPrediction} disabled={loading} className="btn-primary w-full">
            {loading ? "Computing…" : "Run AI Prediction"}
          </button>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <div className="space-y-4">
          {result && (
            <div className="card">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold">Prediction result</h3>
                <span
                  className="badge capitalize"
                  style={{ background: riskColor(result.risk_level) + "22", color: riskColor(result.risk_level) }}
                >
                  {result.risk_level} · {n(result.risk_score)}/100
                </span>
              </div>
              <div className="mt-3 h-3 rounded-full bg-slate-200 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${result.risk_score}%`, background: riskColor(result.risk_level) }}
                />
              </div>
              <div className="grid grid-cols-3 gap-3 mt-4 text-sm">
                <div className="p-3 rounded-lg bg-slate-50">
                  <div className="text-xs text-slate-500">Confidence</div>
                  <div className="font-semibold">{n(result.confidence * 100)}%</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-50">
                  <div className="text-xs text-slate-500">Model</div>
                  <div className="font-semibold capitalize">{result.model}</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-50">
                  <div className="text-xs text-slate-500">Location</div>
                  <div className="font-semibold">{lat.toFixed(3)}, {lng.toFixed(3)}</div>
                </div>
              </div>
              <div className="mt-4">
                <h4 className="text-sm font-semibold mb-2">Factor contributions</h4>
                <div className="space-y-1.5">
                  {(result.factor_contributions || []).map((fc) => (
                    <div key={fc.factor} className="flex items-center gap-2 text-sm">
                      <span className="flex-1">{fc.factor}</span>
                      <span className="text-xs text-slate-500">{n(fc.contribution)} pts</span>
                    </div>
                  ))}
                  {(result.factor_contributions || []).length === 0 && (
                    <p className="text-xs text-slate-500">No dominating factors</p>
                  )}
                </div>
              </div>
              <div className="mt-4 p-3 rounded-lg bg-amber-50 border border-amber-200 text-sm">
                <strong>Recommended action:</strong> {result.recommended_action}
              </div>
            </div>
          )}

          {!result && (
            <div className="card text-sm text-slate-500">
              Click the map to pick a location, adjust the features, then run a
              prediction. Results show the risk score, confidence, model used and
              the factor contributions that drive the score.
            </div>
          )}

          {forecast && (
            <div className="card">
              <h3 className="font-semibold">7-day risk outlook</h3>
              <div className="mt-3 space-y-2">
                {forecast.points?.map((p: any) => (
                  <div key={p.date} className="flex items-center gap-3 text-sm">
                    <span className="w-28 text-xs text-slate-500">{p.date}</span>
                    <div className="flex-1 h-2.5 rounded-full bg-slate-200 overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${p.risk_score}%`, background: riskColor(p.risk_level) }}
                      />
                    </div>
                    <span className="w-24 text-right font-medium" style={{ color: riskColor(p.risk_level) }}>
                      {n(p.risk_score)} · {p.risk_level}
                    </span>
                  </div>
                ))}
              </div>
              <div className="flex gap-2 mt-3">
                <button
                  onClick={async () => {
                    const r = await api.get("/ml/forecast", { params: { days: 7 } });
                    setForecast(r.data);
                  }}
                  className="btn-secondary flex-1"
                >
                  Refresh forecast
                </button>
                <button
                  onClick={async () => {
                    try {
                      const r = await api.get("/reports/export/predictions-csv", { responseType: "blob" });
                      const url = window.URL.createObjectURL(new Blob([r.data]));
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = "risk_predictions.csv";
                      document.body.appendChild(a);
                      a.click();
                      a.remove();
                      window.URL.revokeObjectURL(url);
                    } catch { /* ignore */ }
                  }}
                  className="btn-secondary"
                  title="Export predictions as CSV"
                >
                  ⤓ CSV
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}