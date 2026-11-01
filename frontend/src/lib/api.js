import axios from "axios";

export const API_BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({ baseURL: API_BASE, withCredentials: true });

let refreshing = null;
export const refreshSession = () => {
  refreshing = refreshing || api.post("/auth/refresh").finally(() => { refreshing = null; });
  return refreshing;
};

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const cfg = err.config || {};
    const skip = ["/auth/login", "/auth/register", "/auth/refresh"].some((p) => cfg.url?.includes(p));
    if (err.response?.status === 401 && !cfg._retry && !skip) {
      cfg._retry = true;
      try {
        await refreshSession();
        return api(cfg);
      } catch (_) { /* fallthrough */ }
    }
    return Promise.reject(err);
  }
);

export function errorMessage(e) {
  const detail = e?.response?.data?.detail;
  if (detail == null) return e?.message || "Algo deu errado. Tente novamente.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d?.msg || JSON.stringify(d)).join(" ");
  return detail.msg || String(detail);
}
