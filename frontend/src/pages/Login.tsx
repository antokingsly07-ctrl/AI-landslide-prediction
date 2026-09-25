import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, getErrorMessage } from "../lib/api";
import { useAuthStore } from "../store/authStore";

type Mode = "login" | "register";

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [mode, setMode] = useState<Mode>("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const switchMode = (next: Mode) => {
    setMode(next);
    setError("");
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const trimmedEmail = email.trim();
    if (mode === "register") {
      if (!fullName.trim()) {
        setError(t("auth.full_name_required", "Full name is required"));
        return;
      }
      if (password.length < 6) {
        setError(t("auth.password_min", "Password must be at least 6 characters"));
        return;
      }
      if (password !== confirm) {
        setError(t("auth.password_mismatch", "Passwords do not match"));
        return;
      }
    }
    setLoading(true);
    try {
      const url = mode === "login" ? "/auth/login" : "/auth/register";
      const payload =
        mode === "login"
          ? { email: trimmedEmail, password }
          : { full_name: fullName.trim(), email: trimmedEmail, password, preferred_language: "en" };
      const res = await api.post(url, payload);
      const data = res.data as { access_token: string; user: any };
      setAuth(data.access_token, data.user);
      navigate("/dashboard");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-2xl overflow-hidden">
          <div className="bg-slate-900 px-6 sm:px-8 py-6 sm:py-8 text-center">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-red-500 to-purple-600 flex items-center justify-center text-3xl mb-4">
              ⛰
            </div>
            <h1 className="text-xl font-bold text-white">{t("app")}</h1>
            <p className="text-slate-400 text-sm mt-1">
              North-Eastern India · AI-Driven Risk Assessment
            </p>
          </div>
          <form onSubmit={submit} className="px-5 sm:px-8 py-5 sm:py-6 space-y-4">
            {mode === "register" && (
              <div>
                <label className="label">{t("auth.full_name")}</label>
                <input
                  className="input"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  placeholder="Your name"
                />
              </div>
            )}
            <div>
              <label className="label">{t("auth.email")}</label>
              <input
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="label">{t("auth.password")}</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
              />
            </div>
            {mode === "register" && (
              <div>
                <label className="label">{t("auth.confirm_password", "Confirm Password")}</label>
                <input
                  className="input"
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  required
                  placeholder="••••••••"
                />
              </div>
            )}
            {error && (
              <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
                {error}
              </div>
            )}
            <button className="btn-primary w-full" disabled={loading}>
              {loading
                ? t("common.loading")
                : mode === "login"
                  ? t("auth.sign_in")
                  : t("auth.create_account")}
            </button>
          </form>
          <div className="px-5 sm:px-8 pb-6 text-center text-sm text-slate-500">
            {mode === "login" ? (
              <button type="button" className="text-red-600 hover:underline" onClick={() => switchMode("register")}>
                {t("auth.no_account")} {t("auth.create_account")}
              </button>
            ) : (
              <button type="button" className="text-red-600 hover:underline" onClick={() => switchMode("login")}>
                {t("auth.have_account")} {t("auth.sign_in")}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}