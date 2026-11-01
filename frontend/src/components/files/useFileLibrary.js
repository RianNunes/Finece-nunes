import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";

export const useFileLibrary = () => {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("all");
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [config, setConfig] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const refresh = useCallback(() => setVersion((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    const timer = setTimeout(async () => {
      try {
        const [files, settings] = await Promise.all([
          api.get("/files", { params: { q: query, kind, page }, signal: controller.signal }),
          api.get("/files/config", { signal: controller.signal }),
        ]);
        if (controller.signal.aborted) return;
        const lastPage = Math.max(1, Math.ceil(files.data.total / files.data.page_size));
        if (page > lastPage) { setPage(lastPage); return; }
        setData(files.data); setConfig(settings.data);
      } catch (e) { if (!controller.signal.aborted) setError(errorMessage(e)); }
      finally { if (!controller.signal.aborted) setLoading(false); }
    }, 200);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [query, kind, page, version]);

  return {
    query, kind, page, data, config, loading, error, refresh, setPage,
    search: (value) => { setQuery(value); setPage(1); },
    filter: (value) => { setKind(value); setPage(1); },
    uploaded: () => { setQuery(""); setKind("all"); setPage(1); refresh(); },
  };
};