import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BellRing, X } from "lucide-react";
import { useFetch } from "@/context/AppContext";
import { dateLabel, fmt, today } from "@/lib/finance";

const when = (n) => (n === 0 ? "vence hoje" : n === 1 ? "vence amanhã" : `vence em ${n} dias`);

export const DueAlert = () => {
  const key = `due-dismissed-${today()}`;
  const { data } = useFetch(`/recurring/upcoming?today=${today()}&days=3`);
  const [hidden, setHidden] = useState(() => sessionStorage.getItem(key) === "1");
  const show = !hidden && data?.length > 0;
  const total = data?.reduce((s, r) => s + r.amount, 0) || 0;
  const dismiss = () => { sessionStorage.setItem(key, "1"); setHidden(true); };

  return (
    <AnimatePresence>
      {show && (
        <motion.section role="status" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
          className="glass due-alert rounded-[22px] p-4 sm:p-5 mb-4 flex gap-4 items-start" data-testid="due-alert">
          <span className="stat-icon shrink-0" style={{ "--tone": "var(--amber)" }}><BellRing size={16} /></span>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm" data-testid="due-alert-title">
              {data.length === 1 ? "1 conta vence" : `${data.length} contas vencem`} nos próximos 3 dias · <span className="tabular">{fmt(total)}</span>
            </p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {data.map((r) => (
                <li key={r.id} className={`due-pill ${r.days_left === 0 ? "is-today" : ""}`} data-testid={`due-item-${r.id}`}>
                  <span className="font-medium">{r.name}</span> {when(r.days_left)} ({dateLabel(r.due_date)}) · <span className="tabular">{fmt(r.amount)}</span>
                </li>
              ))}
            </ul>
          </div>
          <button className="icon-btn" aria-label="Dispensar aviso" onClick={dismiss} data-testid="due-alert-dismiss"><X size={16} /></button>
        </motion.section>
      )}
    </AnimatePresence>
  );
};
