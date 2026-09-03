import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import type { Report } from "../types";

export default function Reports() {
  const { t } = useTranslation();
  const [reports, setReports] = useState<Report[]>([]);

  useEffect(() => {
    api.get("/reports").then((r) => setReports(r.data)).catch(() => {});
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t("nav.reports")}</h2>
      <div className="grid gap-3">
        {reports.map((r) => (
          <div key={r.client_id || r.id} className="card">
            <div className="flex items-center justify-between">
              <div className="font-semibold capitalize">{r.report_type}</div>
              <div className="flex items-center gap-2">
                <span className="badge bg-slate-100 text-slate-700 capitalize">{r.severity}</span>
                <span
                  className={`badge ${
                    r.sync_status === "synced" ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {r.sync_status}
                </span>
              </div>
            </div>
            <p className="text-sm text-slate-600 mt-1">{r.description}</p>
            <div className="text-xs text-slate-500 mt-1">
              {r.reported_at ? new Date(r.reported_at).toLocaleString() : ""}
              {r.latitude ? ` · (${r.latitude.toFixed(4)}, ${r.longitude?.toFixed(4)})` : ""}
            </div>
            {r.media?.length > 0 && (
              <div className="flex gap-2 mt-2">
                {r.media.map((m) => (
                  <img key={m.id} src={m.thumb || m.url} alt="" className="w-16 h-16 object-cover rounded-lg" />
                ))}
              </div>
            )}
          </div>
        ))}
        {reports.length === 0 && (
          <div className="card text-center text-slate-500 py-10">No reports yet</div>
        )}
      </div>
    </div>
  );
}
