import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import type { Sensor } from "../types";

export default function Sensors() {
  const { t } = useTranslation();
  const [sensors, setSensors] = useState<Sensor[]>([]);

  useEffect(() => {
    api.get("/sensors").then((r) => setSensors(r.data)).catch(() => {});
  }, []);

  const healthColor = (s: Sensor) =>
    s.status === "active" ? "bg-green-100 text-green-700" : s.status === "warning" ? "bg-amber-100 text-amber-700" : "bg-red-100 text-red-700";

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t("nav.sensors")}</h2>
      <div className="card">
        <div className="flex flex-wrap gap-4 text-sm">
          <span>Total: <strong>{sensors.length}</strong></span>
          <span>Active: <strong>{sensors.filter((s) => s.status === "active").length}</strong></span>
          <span>Warning: <strong>{sensors.filter((s) => s.status === "warning").length}</strong></span>
          <span>Offline: <strong>{sensors.filter((s) => s.status === "offline").length}</strong></span>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {sensors.map((s) => (
          <div key={s.id} className="card">
            <div className="flex items-center justify-between">
              <div className="font-semibold">{s.name}</div>
              <span className={`badge ${healthColor(s)} capitalize`}>{s.status}</span>
            </div>
            <div className="text-xs text-slate-500 capitalize mt-1">{s.sensor_type}</div>
            {s.district_name && (
              <div className="text-xs text-slate-500">{s.district_name}</div>
            )}
            {s.last_reading_at && (
              <div className="text-xs text-slate-400 mt-1">
                Last reading: {new Date(s.last_reading_at).toLocaleString()}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
