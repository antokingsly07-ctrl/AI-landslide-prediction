import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { api } from "../lib/api";
import type { DashboardSummary } from "../types";
import { riskTextClass } from "../lib/utils";

export default function Dashboard() {
  const { t } = useTranslation();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [rainfall, setRainfall] = useState<any[]>([]);
  const [soil, setSoil] = useState<any[]>([]);
  const [riskTrend, setRiskTrend] = useState<any[]>([]);
  const [districtRisk, setDistrictRisk] = useState<any[]>([]);
  const [roadConn, setRoadConn] = useState<any[]>([]);
  const [alertStats, setAlertStats] = useState<any[]>([]);
  const [incidents, setIncidents] = useState<any[]>([]);

  useEffect(() => {
    api
      .get("/dashboard/summary")
      .then((r) => setSummary(r.data))
      .catch(() => {});
    api.get("/dashboard/charts/rainfall").then((r) => setRainfall(r.data)).catch(() => {});
    api.get("/dashboard/charts/soil_moisture").then((r) => setSoil(r.data)).catch(() => {});
    api.get("/dashboard/charts/risk_trend").then((r) => setRiskTrend(r.data)).catch(() => {});
    api.get("/dashboard/charts/district_risk").then((r) => setDistrictRisk(r.data)).catch(() => {});
    api.get("/dashboard/charts/road_connectivity").then((r) => setRoadConn(r.data)).catch(() => {});
    api.get("/dashboard/charts/alerts").then((r) => setAlertStats(r.data)).catch(() => {});
    api.get("/dashboard/charts/incidents").then((r) => setIncidents(r.data)).catch(() => {});
  }, []);

  const color = (sev: string) =>
    sev === "critical" ? "#a855f7" : sev === "high" ? "#ef4444" : sev === "medium" ? "#f97316" : "#eab308";

  return (
    <div className="space-y-6">
      <div className="hidden">
        <span>{t("safety.disclaimer")}</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KPI label={t("dashboard.critical_zones")} value={summary?.critical_zones} color="text-purple-600" />
        <KPI label={t("dashboard.high_risk_zones")} value={summary?.high_risk_zones} color="text-red-600" />
        <KPI label={t("dashboard.active_incidents")} value={summary?.active_incidents} color="text-orange-600" />
        <KPI label={t("dashboard.roads_blocked")} value={summary?.roads_blocked} color="text-red-700" />
        <KPI label={t("dashboard.villages_at_risk")} value={summary?.villages_at_risk} color="text-amber-600" />
        <KPI label={t("dashboard.active_alerts")} value={summary?.active_alerts} color="text-blue-600" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">{t("dashboard.rainfall")}</h3>
            {latest(rainfall, "rain_24h") && (
              <span className="badge bg-blue-100 text-blue-700">now {latest(rainfall, "rain_24h")} mm/24h</span>
            )}
          </div>
          {rainfall.length === 0 ? (
            <EmptyChart />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={rainfall}>
                <XAxis dataKey="date" fontSize={10} />
                <YAxis fontSize={10} />
                <Tooltip />
                <Line type="monotone" dataKey="rain_24h" stroke="#2563eb" name="24h rain (mm)" />
                <Line type="monotone" dataKey="rain_6h" stroke="#7c3aed" name="6h rain (mm)" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">{t("dashboard.soil_moisture")}</h3>
            {latest(soil, "moisture") && (
              <span className="badge bg-green-100 text-green-700">
                now {latest(soil, "moisture")}%{latest(soil, "moisture") >= 70 ? " ⚠ saturated" : ""}
              </span>
            )}
          </div>
          {soil.length === 0 ? (
            <EmptyChart />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={soil}>
                <XAxis dataKey="date" fontSize={10} />
                <YAxis fontSize={10} domain={[0, 100]} />
                <Tooltip />
                <Line type="monotone" dataKey="moisture" stroke="#16a34a" name="moisture %" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">{t("dashboard.risk_trend")}</h3>
            {latest(riskTrend, "risk") && (
              <span className="badge bg-red-100 text-red-700">avg {latest(riskTrend, "risk")}</span>
            )}
          </div>
          {riskTrend.length === 0 ? (
            <EmptyChart />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={riskTrend}>
                <XAxis dataKey="date" fontSize={10} />
                <YAxis fontSize={10} domain={[0, 100]} />
                <Tooltip />
                <Line type="monotone" dataKey="risk" stroke="#ef4444" name="avg risk" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="font-semibold mb-3">{t("dashboard.district_risk")}</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={districtRisk} layout="vertical">
              <XAxis type="number" domain={[0, 100]} fontSize={10} />
              <YAxis type="category" dataKey="district" width={90} fontSize={10} />
              <Tooltip />
              <Bar dataKey="risk_score" name="Risk">
                {districtRisk.map((d, i) => (
                  <Cell key={i} fill={d.risk_score >= 60 ? "#ef4444" : d.risk_score >= 40 ? "#f97316" : "#eab308"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-1 gap-4">
          <div className="card">
            <h3 className="font-semibold mb-3">{t("dashboard.road_connectivity")}</h3>
            <ResponsiveContainer width="100%" height={120}>
              <BarChart data={roadConn}>
                <XAxis dataKey="status" fontSize={10} />
                <YAxis fontSize={10} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" name="Roads">
                  {roadConn.map((r, i) => (
                    <Cell key={i} fill={r.status === "blocked" || r.status === "severely_blocked" ? "#ef4444" : "#16a34a"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="card">
              <h3 className="font-semibold mb-3">{t("dashboard.alerts_chart")}</h3>
              <ResponsiveContainer width="100%" height={120}>
                <PieChart>
                  <Pie data={alertStats} dataKey="count" nameKey="severity" outerRadius={50}>
                    {alertStats.map((a, i) => (
                      <Cell key={i} fill={color(a.severity)} />
                    ))}
                  </Pie>
                  <Legend wrapperStyle={{ fontSize: 10 }} />
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="card">
              <h3 className="font-semibold mb-3">{t("dashboard.incidents_chart")}</h3>
              <ResponsiveContainer width="100%" height={120}>
                <LineChart data={incidents}>
                  <XAxis dataKey="date" fontSize={8} />
                  <YAxis fontSize={10} allowDecimals={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#f97316" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      <div className="card bg-amber-50 border-amber-200">
        <p className="text-sm text-amber-800">
          <strong>⚠ {t("safety.disclaimer")}</strong>
        </p>
      </div>
      <div className="flex gap-2">
        <span className={`badge ${riskTextClass("HAZARD")}`}>{t("common.demo_data")}</span>
      </div>
    </div>
  );
}

function KPI({ label, value, color }: { label: string; value?: number; color: string }) {
  return (
    <div className="card">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className={`kpi-value ${color}`}>{value ?? "—"}</div>
    </div>
  );
}

function latest(rows: any[], key: string): string | null {
  const last = rows[rows.length - 1];
  return last && last[key] != null ? String(last[key]) : null;
}

function EmptyChart() {
  const { t } = useTranslation();
  return (
    <div className="h-[220px] flex items-center justify-center text-sm text-slate-400">
      {t("dashboard.no_data", "No data yet")}
    </div>
  );
}
