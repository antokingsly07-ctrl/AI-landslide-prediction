import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, getErrorMessage } from "../lib/api";
import { useAuthStore } from "../store/authStore";

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/auth/login", {
        email: email.trim(),
        password,
      });
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
          <div className="bg-slate-900 px-8 py-8 text-center">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-red-500 to-purple-600 flex items-center justify-center text-3xl mb-4">
              ⛰
            </div>
            <h1 className="text-xl font-bold text-white">{t("app")}</h1>
            <p className="text-slate-400 text-sm mt-1">
              North-Eastern India · AI-Driven Risk Assessment
            </p>
          </div>
          <form onSubmit={submit} className="px-8 py-6 space-y-4">
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
            {error && (
              <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">
                {error}
              </div>
            )}
            <button className="btn-primary w-full" disabled={loading}>
              {loading ? t("common.loading") : t("auth.sign_in")}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
