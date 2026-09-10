import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "../store/authStore";
import { LANGUAGES } from "../i18n/languages";
import { api } from "../lib/api";
import { useEffect, useState } from "react";
import { useRealtimeAlerts } from "../hooks/useRealtimeAlerts";
import type { Alert } from "../types";

const NAV = [
  { to: "/dashboard", icon: "▤", key: "dashboard" },
  { to: "/gis", icon: "◉", key: "gis" },
  { to: "/predict", icon: "◎", key: "predict" },
  { to: "/incidents", icon: "⚠", key: "incidents" },
  { to: "/report", icon: "✎", key: "field_report" },
  { to: "/alerts", icon: "!", key: "alerts" },
  { to: "/roads", icon: "🛣", key: "roads" },
  { to: "/sensors", icon: "◈", key: "sensors" },
  { to: "/emergency", icon: "🚨", key: "emergency" },
];

export default function Layout() {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [showAlerts, setShowAlerts] = useState(false);
  const [toast, setToast] = useState<Alert | null>(null);

  useRealtimeAlerts((a) => {
    setAlerts((prev) => [a, ...prev].slice(0, 50));
    setToast(a);
    setTimeout(() => setToast((cur) => (cur?.id === a.id ? null : cur)), 8000);
  });

  useEffect(() => {
    api
      .get("/alerts", { params: { status: "active" } })
      .then((r) => setAlerts(r.data))
      .catch(() => {});
    const id = setInterval(() => {
      api
        .get("/alerts", { params: { status: "active" } })
        .then((r) => setAlerts(r.data))
        .catch(() => {});
    }, 30000);
    return () => clearInterval(id);
  }, []);

  const changeLang = async (code: string) => {
    i18n.changeLanguage(code);
    try {
      await api.post("/auth/language", { language: code });
      useAuthStore.getState().setUser({ ...user!, preferred_language: code });
    } catch {
      /* offline or any error */
    }
  };

  const isAdminRole = ["super_admin", "district_admin", "disaster_mgmt"].includes(
    user?.role || ""
  );

  return (
    <div className="flex h-full min-h-screen">
      {toast && (
        <div className="fixed top-4 right-4 z-[60] w-80 bg-white border-2 border-red-200 rounded-xl shadow-2xl p-4 animate-in">
          <div className="flex items-start gap-2">
            <span className="w-8 h-8 rounded-full bg-red-100 text-red-600 flex items-center justify-center shrink-0">!</span>
            <div className="min-w-0">
              <div className="text-sm font-semibold text-slate-800">{toast.title}</div>
              <p className="text-xs text-slate-500 mt-1 line-clamp-2">{toast.message}</p>
            </div>
            <button onClick={() => setToast(null)} className="ml-auto text-slate-400 hover:text-slate-600">✕</button>
          </div>
        </div>
      )}
      <aside className="w-60 bg-slate-900 text-slate-100 flex flex-col shrink-0">
        <div className="px-5 py-5 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded bg-gradient-to-br from-red-500 to-purple-600 flex items-center justify-center font-bold text-white">
              ⛰
            </div>
            <div>
              <div className="font-semibold leading-tight text-sm">Landslide</div>
              <div className="text-xs text-slate-400">Early Warning &amp; Monitoring</div>
            </div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-slate-800 text-white"
                    : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              <span className="w-5 text-center">{n.icon}</span>
              <span>{t(`nav.${n.key}`)}</span>
            </NavLink>
          ))}
          {isAdminRole && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? "bg-slate-800 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
                }`
              }
            >
              <span className="w-5 text-center">⚙</span>
              <span>{t("nav.admin")}</span>
            </NavLink>
          )}
          <NavLink
            to="/health"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive ? "bg-slate-800 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`
            }
          >
            <span className="w-5 text-center">♥</span>
            <span>{t("nav.health")}</span>
          </NavLink>
        </nav>
        <div className="px-4 py-4 border-t border-slate-800 text-xs text-slate-400">
          {t("safety.disclaimer")}
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
          <h1 className="text-lg font-semibold">{t("app")}</h1>
          <div className="flex items-center gap-4">
            <select
              value={i18n.language}
              onChange={(e) => changeLang(e.target.value)}
              className="input !w-auto !py-1.5 text-sm"
              aria-label={t("auth.language")}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
            <div className="relative">
              <button
                onClick={() => setShowAlerts((s) => !s)}
                className="relative w-10 h-10 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center"
                aria-label={t("alert.title")}
              >
                🔔
                {alerts.length > 0 && (
                  <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white text-xs flex items-center justify-center">
                    {alerts.length}
                  </span>
                )}
              </button>
              {showAlerts && (
                <div className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-xl shadow-lg z-50 max-h-96 overflow-y-auto">
                  <div className="px-4 py-3 border-b font-semibold text-sm">
                    {t("alert.title")} ({alerts.length})
                  </div>
                  {alerts.length === 0 && (
                    <div className="p-4 text-sm text-slate-500">No active alerts</div>
                  )}
                  {alerts.map((a) => (
                    <div key={a.id} className="px-4 py-3 border-b last:border-0">
                      <div className="flex items-center gap-2">
                        <span className="badge bg-red-100 text-red-700">{a.severity}</span>
                        <span className="text-sm font-medium">{a.title}</span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">{a.message}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="text-right">
              <div className="text-sm font-medium">{user?.full_name}</div>
              <div className="text-xs text-slate-500 capitalize">{user?.role}</div>
            </div>
            <button onClick={logout} className="btn-secondary !py-1.5">
              {t("auth.logout")}
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
