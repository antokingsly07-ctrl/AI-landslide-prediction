import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, getErrorMessage } from "../lib/api";
import type { RiskLevel } from "../types";

interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role?: string;
  role_id?: string;
  is_active: boolean;
}

interface Sensor {
  id: string;
  name: string;
  sensor_type: string;
  status: string;
  district_id?: string;
  latitude?: number;
  longitude?: number;
}

interface AuditRow {
  id: string;
  user_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: string;
  created_at: string;
}

const RISK_KEYS: RiskLevel[] = ["VERY_LOW", "LOW", "MODERATE", "HIGH", "CRITICAL"];

export default function Admin() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<"users" | "sensors" | "audit" | "thresholds">("users");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [thresholds, setThresholds] = useState<Record<string, [number, number]>>({});
  const [districts, setDistricts] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [newSensorName, setNewSensorName] = useState("");
  const [newSensorType, setNewSensorType] = useState("soil_moisture");

  const load = async () => {
    try {
      const [u, s, aud] = await Promise.all([
        api.get("/auth/users"),
        api.get("/admin/sensors"),
        api.get("/admin/audit-logs"),
      ]);
      setUsers(u.data);
      setSensors(s.data);
      setAudit(aud.data);
    } catch {
      /* role-restricted; ignore */
    }
    api.get("/admin/thresholds").then((r) => {
      const data = r.data;
      setThresholds(data.risk_levels ?? (typeof data === "object" && data.VERY_LOW ? data : {}));
    }).catch(() => {});
    api.get("/admin/districts").then((r) => setDistricts(r.data)).catch(() => {});
  };

  useEffect(() => {
    load();
  }, []);

  const toggleUser = async (id: string, active: boolean) => {
    try {
      await api.patch(`/admin/users/${id}`, { is_active: active });
      await load();
    } catch (e) {
      setMessage(getErrorMessage(e));
    }
  };

  const createSensor = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const dist = districts[0];
      await api.post("/sensors", {
        name: newSensorName,
        sensor_type: newSensorType,
        district_id: dist?.id,
        latitude: 26.2,
        longitude: 93.0,
      });
      setNewSensorName("");
      await load();
      setMessage("Sensor created");
    } catch (e) {
      setMessage(getErrorMessage(e));
    }
  };

  const updateThreshold = async () => {
    try {
      await api.post("/admin/thresholds", { risk_levels: thresholds });
      setMessage("Thresholds saved to database (applied immediately)");
    } catch (e) {
      setMessage(getErrorMessage(e));
    }
  };

  const TABS: { key: typeof tab; label: string }[] = [
    { key: "users", label: t("admin.users") },
    { key: "sensors", label: t("admin.sensors") },
    { key: "thresholds", label: t("admin.thresholds") },
    { key: "audit", label: "Audit Logs" },
  ];

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t("nav.admin")}</h2>
      <div className="flex gap-2 flex-wrap">
        {TABS.map((tb) => (
          <button
            key={tb.key}
            onClick={() => setTab(tb.key)}
            className={`btn ${
              tab === tb.key ? "bg-blue-600 text-white" : "bg-slate-200 text-slate-700 hover:bg-slate-300"
            }`}
          >
            {tb.label}
          </button>
        ))}
      </div>
      {message && <div className="text-sm bg-blue-50 text-blue-700 rounded-lg px-3 py-2">{message}</div>}

      {tab === "users" && (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-2 pr-4">Name</th>
                <th className="py-2 pr-4">Email</th>
                <th className="py-2 pr-4">Role</th>
                <th className="py-2">Active</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b last:border-0">
                  <td className="py-2 pr-4">{u.full_name}</td>
                  <td className="py-2 pr-4">{u.email}</td>
                  <td className="py-2 pr-4 capitalize">{u.role || "citizen"}</td>
                  <td className="py-2">
                    <input
                      type="checkbox"
                      checked={u.is_active}
                      onChange={(e) => toggleUser(u.id, e.target.checked)}
                      className="accent-blue-600"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "sensors" && (
        <div className="space-y-4">
          <form onSubmit={createSensor} className="card flex gap-2 items-end">
            <div className="flex-1">
              <label className="label">Name</label>
              <input className="input" value={newSensorName} onChange={(e) => setNewSensorName(e.target.value)} required />
            </div>
            <div>
              <label className="label">Type</label>
              <select className="input" value={newSensorType} onChange={(e) => setNewSensorType(e.target.value)}>
                {[ "soil_moisture", "rain_gauge", "tilt", "inclinometer", "piezometer", "extensometer", "ground_movement", "geophone", "temperature"].map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <button className="btn-primary">Add</button>
          </form>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {sensors.map((s) => (
              <div key={s.id} className="card">
                <div className="font-semibold">{s.name}</div>
                <div className="text-xs text-slate-500 capitalize">{s.sensor_type}</div>
                <div className="text-xs text-slate-500">{s.status}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "thresholds" && (
        <div className="card max-w-lg space-y-3">
          {RISK_KEYS.map((k) => (
            <div key={k} className="flex items-center gap-2">
              <span className="w-28 text-sm capitalize">{k.replace(/_/g, " ")}</span>
              <input
                className="input"
                type="number"
                value={thresholds[k]?.[0] ?? ""}
                onChange={(e) =>
                  setThresholds({ ...thresholds, [k]: [Number(e.target.value), thresholds[k]?.[1] ?? 20] })
                }
              />
              <span>–</span>
              <input
                className="input"
                type="number"
                value={thresholds[k]?.[1] ?? ""}
                onChange={(e) =>
                  setThresholds({ ...thresholds, [k]: [thresholds[k]?.[0] ?? 0, Number(e.target.value)] })
                }
              />
            </div>
          ))}
          <button className="btn-primary" onClick={updateThreshold}>
            Save thresholds
          </button>
        </div>
      )}

      {tab === "audit" && (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-2 pr-4">Time</th>
                <th className="py-2 pr-4">Action</th>
                <th className="py-2 pr-4">Resource</th>
                <th className="py-2">Details</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((a) => (
                <tr key={a.id} className="border-b last:border-0">
                  <td className="py-2 pr-4 text-xs whitespace-nowrap">{new Date(a.created_at).toLocaleString()}</td>
                  <td className="py-2 pr-4">{a.action}</td>
                  <td className="py-2 pr-4 text-xs">{a.resource_type}</td>
                  <td className="py-2 text-xs text-slate-600">{a.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
