import { useState } from "react";
import { toast } from "sonner";
import { Plus, Layers, Trash2 } from "lucide-react";
import { api, errorMessage } from "@/lib/api";
import { fmt, getCategory, monthLabel } from "@/lib/finance";
import { ConfirmModal, originFrom } from "@/components/GlassModal";
import { Empty } from "@/components/MonthSwitcher";
import { useApp, useFetch } from "@/context/AppContext";

export const Installments = ({ onNew }) => {
  const { bump } = useApp();
  const { data: items } = useFetch("/installments");
  const [confirm, setConfirm] = useState(null);

  const remove = async () => {
    await api.delete(`/installments/${confirm.id}`).catch((e) => toast.error(errorMessage(e)));
    toast.success("Compra parcelada excluída"); setConfirm(null); bump();
  };

  return (
    <section className="glass card" data-testid="installments-card">
      <div className="card-head">
        <h2 className="card-title">Compras parceladas</h2>
        <button className="chip-btn" data-testid="installment-add-button" onClick={onNew}><Plus size={15} /> Parcelada</button>
      </div>
      {items && !items.length ? <Empty icon={Layers} text="Lance uma compra parcelada e as parcelas entram sozinhas nos próximos meses." testId="installments-empty" /> : (
        <ul className="space-y-4">
          {items?.map((g) => {
            const c = getCategory(g.category); const Icon = c.icon; const pct = (g.paid / g.installments) * 100;
            return (
              <li key={g.group_id} data-testid={`installment-${g.group_id}`}>
                <div className="flex items-center gap-3">
                  <span className="cat-dot" style={{ "--c": c.color }}><Icon size={15} /></span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate">{g.description}</p>
                    <p className="text-xs text-slate-400 tabular">{g.installments}x de {fmt(g.installment_amount)} · {monthLabel(g.start_date.slice(0, 7), true)} a {monthLabel(g.end_date.slice(0, 7), true)} {g.end_date.slice(0, 4)}</p>
                  </div>
                  <span className="tabular text-sm">{fmt(g.total)}</span>
                  <button className="icon-btn" aria-label="Excluir parcelada" data-testid={`installment-delete-${g.group_id}`}
                    onClick={(e) => setConfirm({ origin: originFrom(e), id: g.group_id, title: "Excluir compra parcelada", message: `Excluir "${g.description}" e todas as ${g.installments} parcelas?` })}><Trash2 size={14} /></button>
                </div>
                <div className="bar mt-2 ml-11"><div className="bar-fill" style={{ width: `${pct}%`, background: "var(--blue)" }} /></div>
                <p className="text-[11px] text-slate-400 mt-1 ml-11 tabular">{g.paid} de {g.installments} parcelas</p>
              </li>
            );
          })}
        </ul>
      )}
      <ConfirmModal state={confirm} onClose={() => setConfirm(null)} onConfirm={remove} testId="installment-confirm" />
    </section>
  );
};
