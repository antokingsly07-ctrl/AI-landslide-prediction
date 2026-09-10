import { Navigate, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "./store/authStore";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import GisMap from "./pages/GisMap";
import IncidentReport from "./pages/IncidentReport";
import Incidents from "./pages/Incidents";
import Alerts from "./pages/Alerts";
import Roads from "./pages/Roads";
import Sensors from "./pages/Sensors";
import Reports from "./pages/Reports";
import Health from "./pages/Health";
import Emergency from "./pages/Emergency";
import Predict from "./pages/Predict";
import Admin from "./pages/Admin";
import Layout from "./components/Layout";
import { useOnline } from "./hooks/useOnline";
import { syncPendingReports } from "./lib/syncService";
import { isOnline } from "./lib/syncService";
import { useEffect } from "react";

function Protected({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const online = useOnline();
  const { t } = useTranslation();

  useEffect(() => {
    if (online) {
      syncPendingReports().catch(() => {});
    }
  }, [online]);

  return (
    <div>
      {!isOnline() && (
        <div className="fixed top-0 inset-x-0 z-50 bg-amber-500 text-white text-center py-1 text-sm font-medium">
          {t("common.offline")} — {t("report.saved_offline")}
        </div>
      )}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <Protected>
              <Layout />
            </Protected>
          }
        >
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/gis" element={<GisMap />} />
          <Route path="/report" element={<IncidentReport />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/roads" element={<Roads />} />
          <Route path="/sensors" element={<Sensors />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/health" element={<Health />} />
          <Route path="/emergency" element={<Emergency />} />
          <Route path="/predict" element={<Predict />} />
          <Route path="/admin" element={<Admin />} />
        </Route>
      </Routes>
    </div>
  );
}
