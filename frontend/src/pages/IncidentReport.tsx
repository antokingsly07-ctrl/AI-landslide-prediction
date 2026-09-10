import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../lib/api";
import { useOnline } from "../hooks/useOnline";
import {
  savePendingReport,
  getPendingReports,
  removePendingReport,
  type PendingReport,
} from "../store/offlineDb";
import { syncPendingReports, generateClientId } from "../lib/syncService";

const REPORT_TYPES = [
  "slope_crack",
  "slope_movement",
  "rockfall",
  "blocked_road",
  "flooding",
  "other",
];
const SEVERITIES = ["low", "medium", "high", "critical"];

export default function IncidentReport() {
  const { t } = useTranslation();
  const online = useOnline();
  const fileRef = useRef<HTMLInputElement>(null);
  const [reportType, setReportType] = useState("slope_crack");
  const [severity, setSeverity] = useState("medium");
  const [description, setDescription] = useState("");
  const [lat, setLat] = useState<number>(26.2);
  const [lng, setLng] = useState<number>(93.0);
  const [locManual, setLocManual] = useState(false);
  const [photos, setPhotos] = useState<string[]>([]);
  const [message, setMessage] = useState<{ kind: "ok" | "err" | "info"; text: string } | null>(null);
  const [locating, setLocating] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setMessage({ kind: "err", text: "Geolocation unavailable" });
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(Number(pos.coords.latitude.toFixed(5)));
        setLng(Number(pos.coords.longitude.toFixed(5)));
        setLocManual(false);
        setLocating(false);
      },
      () => {
        setLocating(false);
        setMessage({ kind: "err", text: "Could not get location; enter manually" });
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const onPhotos = (files: FileList | null) => {
    if (!files) return;
    Array.from(files)
      .filter((f) => f.type.startsWith("image/"))
      .slice(0, 4 - photos.length)
      .forEach((f) => {
        const reader = new FileReader();
        reader.onload = () => setPhotos((p) => [...p, reader.result as string]);
        reader.readAsDataURL(f);
      });
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    if (lat === undefined || lng === undefined) {
      setMessage({ kind: "err", text: "Location required" });
      return;
    }
    const clientId = generateClientId();
    const payload = {
      client_id: clientId,
      report_type: reportType,
      severity,
      description,
      latitude: lat,
      longitude: lng,
      device_location_manual: locManual,
      photos,
    };

    if (online) {
      try {
        await api.post("/reports", payload);
        setMessage({ kind: "ok", text: "Report submitted successfully" });
        reset();
        return;
      } catch (err: any) {
        if (err?.response?.status === 401) {
          setMessage({ kind: "err", text: "Session expired; please log in" });
          return;
        }
        // fall through to offline save on network error
      }
    }

    const pending: PendingReport = {
      client_id: clientId,
      report_type: reportType,
      severity,
      description,
      latitude: lat,
      longitude: lng,
      device_location_manual: locManual,
      reported_at: new Date().toISOString(),
      photos,
      sync_status: "pending_sync",
      retry_count: 0,
    };
    await savePendingReport(pending);
    setMessage({ kind: "info", text: t("report.saved_offline") });
    reset();
    refreshPending();
  };

  const refreshPending = async () => {
    const p = await getPendingReports();
    setPendingCount(p.length);
  };

  const reset = () => {
    setReportType("slope_crack");
    setSeverity("medium");
    setDescription("");
    setPhotos([]);
    if (fileRef.current) fileRef.current.value = "";
  };

  const doSync = async () => {
    const res = await syncPendingReports();
    setMessage({ kind: "ok", text: `Synced ${res.synced} report(s)` });
    refreshPending();
  };

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{t("report.title")}</h2>
        <div className="flex items-center gap-3">
          <span
            className={`badge ${online ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}
          >
            {online ? t("common.online") : t("common.offline")}
          </span>
          {pendingCount > 0 && (
            <button onClick={doSync} className="btn-secondary !py-1.5">
              Sync ({pendingCount})
            </button>
          )}
        </div>
      </div>

      <form onSubmit={submit} className="card space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">{t("report.type")}</label>
            <select className="input" value={reportType} onChange={(e) => setReportType(e.target.value)}>
              {REPORT_TYPES.map((rt) => (
                <option key={rt} value={rt}>
                  {t(`report.${rt}`)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">{t("report.severity")}</label>
            <select className="input" value={severity} onChange={(e) => setSeverity(e.target.value)}>
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {t(`report.${s}`)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="label">{t("report.description")}</label>
          <textarea
            className="input min-h-[90px]"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what you observed..."
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="label !mb-0">
              Location ({lat.toFixed(4)}, {lng.toFixed(4)})
            </label>
            <button type="button" onClick={useCurrentLocation} className="btn-secondary !py-1 text-xs">
              {locating ? t("common.loading") : t("report.use_current_location")}
            </button>
          </div>
          <div className="flex gap-2">
            <input
              className="input"
              type="number"
              step="0.0001"
              value={lat}
              onChange={(e) => {
                setLat(Number(e.target.value));
                setLocManual(true);
              }}
              aria-label={t("report.latitude")}
            />
            <input
              className="input"
              type="number"
              step="0.0001"
              value={lng}
              onChange={(e) => {
                setLng(Number(e.target.value));
                setLocManual(true);
              }}
              aria-label={t("report.longitude")}
            />
          </div>
        </div>

        <div>
          <button type="button" onClick={() => fileRef.current?.click()} className="btn-secondary">
            📷 {t("report.add_photos")} ({photos.length}/4)
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => onPhotos(e.target.files)}
          />
          {photos.length > 0 && (
            <div className="flex gap-2 mt-2 flex-wrap">
              {photos.map((p, i) => (
                <div key={i} className="relative">
                  <img src={p} alt="" className="w-16 h-16 object-cover rounded-lg" />
                  <button
                    type="button"
                    className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white text-xs"
                    onClick={() => setPhotos((pArr) => pArr.filter((_, idx) => idx !== i))}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {message && (
          <div
            className={`text-sm rounded-lg px-3 py-2 ${
              message.kind === "ok"
                ? "bg-green-50 text-green-700"
                : message.kind === "err"
                ? "bg-red-50 text-red-600"
                : "bg-amber-50 text-amber-700"
            }`}
          >
            {message.text}
          </div>
        )}

        <button type="submit" className="btn-primary w-full">
          {t("report.submit")}
        </button>
      </form>

      <p className="text-xs text-slate-500">
        {online
          ? "Submitted directly to the server."
          : "Saved on this device and synced automatically when you're back online."}{" "}
        {t("safety.disclaimer")}
      </p>
    </div>
  );
}
