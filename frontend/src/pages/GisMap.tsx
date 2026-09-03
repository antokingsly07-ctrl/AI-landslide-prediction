import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, CircleMarker, Popup } from "react-leaflet";
import { useTranslation } from "react-i18next";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { api } from "../lib/api";
import type { RiskZone, Incident, Road, Sensor, Alert } from "../types";
import { riskColor } from "../lib/utils";

const NE_CENTER: [number, number] = [26.2, 93.0];

export default function GisMap() {
  const { t } = useTranslation();
  const [zones, setZones] = useState<RiskZone[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [roads, setRoads] = useState<Road[]>([]);
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showZones, setShowZones] = useState(true);
  const [showIncidents, setShowIncidents] = useState(true);
  const [showRoads, setShowRoads] = useState(true);
  const [showSensors, setShowSensors] = useState(false);

  useEffect(() => {
    api.get("/risk/zones", { params: { limit: 200 } }).then((r) => setZones(r.data)).catch(() => {});
    api.get("/incidents").then((r) => setIncidents(r.data)).catch(() => {});
    api.get("/roads").then((r) => setRoads(r.data)).catch(() => {});
    api.get("/sensors").then((r) => setSensors(r.data)).catch(() => {});
    api.get("/alerts").then((r) => setAlerts(r.data)).catch(() => {});
  }, []);

  const incidentIcon = L.divIcon({
    className: "",
    html: `<div style="width:14px;height:14px;background:#ef4444;border-radius:50%;border:2px solid white;box-shadow:0 0 4px rgba(0,0,0,.5)"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
  const roadIcon = L.divIcon({
    className: "",
    html: `<div style="width:10px;height:10px;background:#3b82f6;border-radius:2px;border:1px solid white"></div>`,
    iconSize: [10, 10],
    iconAnchor: [5, 5],
  });
  const sensorIcon = L.divIcon({
    className: "",
    html: `<div style="width:12px;height:12px;background:#10b981;clip-path:polygon(50% 0,100% 100%,0 100%);filter:drop-shadow(0 0 3px rgba(0,0,0,.5))"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 10],
  });

  return (
    <div className="h-[calc(100vh-140px)] flex flex-col">
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-2 mb-3 flex flex-wrap gap-2 items-center">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={showZones} onChange={(e) => setShowZones(e.target.checked)} className="accent-blue-600" />
          <span className="inline-block w-3 h-3 rounded-full" style={{ background: "#f97316" }} />
          Risk zones
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={showIncidents} onChange={(e) => setShowIncidents(e.target.checked)} className="accent-red-600" />
          <span className="inline-block w-3 h-3 rounded-full" style={{ background: "#ef4444" }} />
          Incidents
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={showRoads} onChange={(e) => setShowRoads(e.target.checked)} className="accent-blue-600" />
          <span className="inline-block w-3 h-3 rounded-full" style={{ background: "#3b82f6" }} />
          Roads
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={showSensors} onChange={(e) => setShowSensors(e.target.checked)} className="accent-emerald-600" />
          <span className="inline-block w-3 h-3 rounded-full" style={{ background: "#10b981" }} />
          Sensors
        </label>
        <span className="ml-auto text-xs text-slate-500">
          {alerts.filter((a) => a.status === "active").length} active alerts
        </span>
      </div>
      <div className="flex-1 rounded-xl overflow-hidden border border-slate-200 shadow-sm">
        <MapContainer center={NE_CENTER} zoom={7} style={{ height: "100%", width: "100%" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {showZones &&
            zones
              .filter((z) => z.latitude && z.longitude)
              .map((z) => (
                <CircleMarker
                  key={z.id}
                  center={[z.latitude!, z.longitude!]}
                  radius={z.risk_level === "CRITICAL" ? 14 : z.risk_level === "HIGH" ? 10 : 7}
                  pathOptions={{
                    color: riskColor(z.risk_level),
                    fillColor: riskColor(z.risk_level),
                    fillOpacity: 0.5,
                  }}
                >
                  <Popup>
                    <strong>{z.name}</strong>
                    <div>{z.district_name || ""}</div>
                    <div className="font-semibold" style={{ color: riskColor(z.risk_level) }}>
                      {t(`risk.${z.risk_level}`)} · {z.risk_score}
                    </div>
                    <div>Pop: {z.population}</div>
                  </Popup>
                </CircleMarker>
              ))}
          {showIncidents &&
            incidents
              .filter((i) => i.latitude && i.longitude)
              .map((i) => (
                <Marker key={i.id} position={[i.latitude!, i.longitude!]} icon={incidentIcon}>
                  <Popup>
                    <strong>{i.incident_type}</strong>
                    <div>Status: {i.verification_status}</div>
                    <div>Severity: {i.severity}</div>
                  </Popup>
                </Marker>
              ))}
          {showRoads &&
            roads
              .filter((r) => r.latitude && r.longitude)
              .map((r) => (
                <Marker key={r.id} position={[r.latitude!, r.longitude!]} icon={roadIcon}>
                  <Popup>
                    <strong>{r.name}</strong>
                    <div>Status: {r.status}</div>
                  </Popup>
                </Marker>
              ))}
          {showSensors &&
            sensors
              .filter((s) => s.latitude && s.longitude)
              .map((s) => (
                <Marker key={s.id} position={[s.latitude!, s.longitude!]} icon={sensorIcon}>
                  <Popup>
                    <strong>{s.name}</strong>
                    <div>Type: {s.sensor_type}</div>
                    <div>Status: {s.status}</div>
                  </Popup>
                </Marker>
              ))}
        </MapContainer>
      </div>
    </div>
  );
}
