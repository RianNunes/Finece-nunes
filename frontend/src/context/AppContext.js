import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { currentMonth } from "@/lib/finance";

const Ctx = createContext(null);

export const AppProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [month, setMonth] = useState(currentMonth());
  const [version, setVersion] = useState(0);

  useEffect(() => {
    api.get("/auth/me").then((r) => setUser(r.data)).catch(() => setUser(false));
  }, []);

  const login = async (email, password) => setUser((await api.post("/auth/login", { email, password })).data);
  const register = async (name, email, password) => setUser((await api.post("/auth/register", { name, email, password })).data);
  const logout = async () => {
    await api.post("/auth/logout").catch(() => {});
    setUser(false);
  };
  const bump = useCallback(() => setVersion((v) => v + 1), []);

  return (
    <Ctx.Provider value={{ user, setUser, login, register, logout, month, setMonth, version, bump }}>
      {children}
    </Ctx.Provider>
  );
};

export const useApp = () => useContext(Ctx);

export function useFetch(path, deps = []) {
  const { version } = useApp();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    let alive = true;
    api.get(path).then((r) => alive && (setData(r.data), setError(null))).catch((e) => alive && setError(e));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, version, ...deps]);
  return { data, error, loading: data === null && !error };
}
