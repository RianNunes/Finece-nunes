import { useState } from "react";
import { toast } from "sonner";
import { Plus, Repeat, Trash2 } from "lucide-react";
import { api, errorMessage } from "@/lib/api";
import { EXPENSE_CATEGORIES, fmt, getCategory, parseAmount } from "@/lib/finance";
import { GlassModal, ConfirmModal, originFrom } from "@/components/GlassModal";
import { CategoryPicker } from "@/components/CategoryPicker";
import { Empty } from "@/components/MonthSwitcher";
import { useApp, useFetch } from "@/context/AppContext";

export const Recurring = () => {
  const { bump, month } = useApp();
  const { data: items } = useFetch("/recurring");
  const [form, setForm] = useState(null);
  const [confirm, setConfirm] = useState(null);
  const total = items?.filter((r) => r.active).reduce((s, r) => s + r.amount, 0) || 0;

  const save = async (e) => {
    e.preventDefault();
    const amount = parseAmount(form.amount);
    if (!(amount > 0)) return toast.error("Informe um valor válido");
    const body = { name: form.name, amount, day: Number(form.day), category: form.category, active: form.active, start_month: form.start_month || month };
    try {
      if (form.id) await api.put(`/recurring/${form.id}`, body); else await api.post("/recurring", body);
      toast.success("Recorrente salva"); setForm(null); bump();
    } catch (err) { toast.error(errorMessage(err)); }
  };
  const remove = async () => {
    await api.delete(`/recurring/${confirm.id}`).catch((e) => toast.error(errorMessage(e)));
    toast.success("Recorrente excluída"); setConfirm(null); setForm(null); bump();
  };

  return (
    <section className="glass card" data-testid="recurring-card">
      <div className="card-head">
        <div>
          <h2 className="card-title">Despesas recorrentes</h2>
          <p className="text-xs text-slate-400 tabular" data-testid="recurring-total">{fmt(total)} por mês</p>
        </div>
        <button className="chip-btn" data-testid="recurring-add-button" onClick={(e) => setForm({ origin: originFrom(e), name: "", amount: "", day: 10, category: "contas", active: true })}><Plus size={15} /> Recorrente</button>
      </div>
      {items && !items.length ? <Empty icon={Repeat} text="Cadastre contas fixas como aluguel, internet e assinaturas." testId="recurring-empty" /> : (
        <ul className="divide-y divide-white/5">
          {items?.map((r) => {
            const c = getCategory(r.category); const Icon = c.icon;
            return (
              <li key={r.id}>
                <button className="row w-full" data-testid={`recurring-row-${r.id}`} onClick={(e) => setForm({ origin: originFrom(e), ...r, amount: String(r.amount).replace(".", ",") })}>
                  <span className="cat-dot" style={{ "--c": c.color }}><Icon size={15} /></span>
                  <span className="flex-1 min-w-0 text-left"><span className="block truncate text-sm">{r.name}</span><span className="text-xs text-slate-400">todo dia {r.day} · {c.label}{!r.active && " · pausada"}</span></span>
                  <span className={`tabular text-sm ${r.active ? "text-red-300" : "text-slate-500 line-through"}`}>-{fmt(r.amount)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <GlassModal open={!!form} onClose={() => setForm(null)} origin={form?.origin} title={form?.id ? "Editar recorrente" : "Nova recorrente"} wide testId="recurring-modal">
        {form && (
          <form onSubmit={save} className="space-y-4">
            <label className="field"><span>Nome</span><input value={form.name} maxLength={120} placeholder="Ex.: Internet" onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="recurring-name-input" required /></label>
            <div className="grid grid-cols-2 gap-3">
              <label className="field"><span>Valor (R$)</span><input inputMode="decimal" placeholder="0,00" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} data-testid="recurring-amount-input" required /></label>
              <label className="field"><span>Dia do vencimento</span><input type="number" min={1} max={31} value={form.day} onChange={(e) => setForm({ ...form, day: e.target.value })} data-testid="recurring-day-input" required /></label>
            </div>
            <CategoryPicker categories={EXPENSE_CATEGORIES} value={form.category} onChange={(category) => setForm({ ...form, category })} testId="recurring-category" />
            <label className="flex items-center gap-3 text-sm"><input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} data-testid="recurring-active-checkbox" className="accent-emerald-400 h-4 w-4" /> Ativa (conta nos meses)</label>
            <div className="flex gap-3">
              {form.id && <button type="button" className="btn-ghost text-red-300" aria-label="Excluir" data-testid="recurring-delete-button"
                onClick={(e) => setConfirm({ origin: originFrom(e), id: form.id, title: "Excluir recorrente", message: `Excluir "${form.name}"? Ela deixa de aparecer em todos os meses.` })}><Trash2 size={16} /></button>}
              <button className="btn-primary flex-1" data-testid="recurring-submit-button">Salvar</button>
            </div>
          </form>
        )}
      </GlassModal>
      <ConfirmModal state={confirm} onClose={() => setConfirm(null)} onConfirm={remove} testId="recurring-confirm" />
    </section>
  );
};
