import { useState } from "react";
import { toast } from "sonner";
import { Plus, Wallet, Trash2 } from "lucide-react";
import { api, errorMessage } from "@/lib/api";
import { EXPENSE_CATEGORIES, fmt, getCategory, monthLabel, parseAmount, progressColor } from "@/lib/finance";
import { GlassModal, ConfirmModal, originFrom } from "@/components/GlassModal";
import { CategoryPicker } from "@/components/CategoryPicker";
import { Empty } from "@/components/MonthSwitcher";
import { useApp } from "@/context/AppContext";

const BudgetRow = ({ b, onEdit }) => {
  const c = getCategory(b.category);
  const pct = b.limit ? (b.spent / b.limit) * 100 : 0;
  return (
    <button className="w-full text-left group" onClick={onEdit} data-testid={`budget-row-${b.category}`}>
      <div className="flex items-center justify-between text-sm mb-1.5">
        <span className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{ background: c.color }} />{c.label}
          {b.override && <span className="tag" data-testid={`budget-override-tag-${b.category}`}>só {monthLabel(b.month, true)}</span>}</span>
        <span className="tabular text-slate-400"><span className="text-slate-100">{fmt(b.spent)}</span> / {fmt(b.limit)}</span>
      </div>
      <div className="bar" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label={`Orçamento ${c.label}`}>
        <div className="bar-fill" style={{ width: `${Math.min(pct, 100)}%`, background: progressColor(pct) }} />
      </div>
      <p className="text-[11px] mt-1 tabular" style={{ color: progressColor(pct) }}>
        {pct > 100 ? `Estourou ${fmt(b.spent - b.limit)}` : `${Math.round(pct)}% usado · resta ${fmt(b.limit - b.spent)}`}
      </p>
    </button>
  );
};

export const Budgets = ({ budgets }) => {
  const { bump, month } = useApp();
  const [form, setForm] = useState(null);
  const [confirm, setConfirm] = useState(null);

  const save = async (e) => {
    e.preventDefault();
    const limit = parseAmount(form.limit);
    if (!(limit > 0)) return toast.error("Informe um limite válido");
    try {
      await api.put("/budgets", { category: form.category, limit, month: form.onlyMonth ? month : null });
      toast.success("Orçamento salvo");
      setForm(null);
      bump();
    } catch (err) { toast.error(errorMessage(err)); }
  };
  const remove = async () => {
    await api.delete(`/budgets/${confirm.category}`, { params: confirm.month ? { month: confirm.month } : {} }).catch((e) => toast.error(errorMessage(e)));
    toast.success(confirm.month ? "Limite do mês removido" : "Orçamento removido");
    setConfirm(null);
    setForm(null);
    bump();
  };

  return (
    <section className="glass card" data-testid="budgets-card">
      <div className="card-head">
        <h2 className="card-title">Orçamentos do mês</h2>
        <button className="chip-btn" data-testid="budget-add-button" onClick={(e) => setForm({ origin: originFrom(e), category: "mercado", limit: "", onlyMonth: false })}><Plus size={15} /> Limite</button>
      </div>
      {!budgets?.length ? <Empty icon={Wallet} text="Defina limites por categoria para acompanhar seus gastos." testId="budgets-empty" /> : (
        <div className="space-y-4">
          {budgets.map((b) => <BudgetRow key={b.category} b={b} onEdit={(e) => setForm({ origin: originFrom(e), category: b.category, limit: String(b.limit).replace(".", ","), existing: true, onlyMonth: b.override, override: b.override, defaultLimit: b.default_limit })} />)}
        </div>
      )}
      <GlassModal open={!!form} onClose={() => setForm(null)} origin={form?.origin} title={form?.existing ? "Editar orçamento" : "Novo orçamento"} wide testId="budget-modal">
        {form && (
          <form onSubmit={save} className="space-y-5">
            <CategoryPicker categories={EXPENSE_CATEGORIES} value={form.category} onChange={(category) => setForm({ ...form, category })} testId="budget-category" />
            <label className="field"><span>Limite mensal (R$)</span>
              <input inputMode="decimal" placeholder="0,00" value={form.limit} onChange={(e) => setForm({ ...form, limit: e.target.value })} data-testid="budget-limit-input" required />
            </label>
            <label className="flex items-start gap-3 text-sm cursor-pointer">
              <input type="checkbox" checked={form.onlyMonth} onChange={(e) => setForm({ ...form, onlyMonth: e.target.checked })} data-testid="budget-only-month-checkbox" className="accent-sky-400 h-4 w-4 mt-0.5" />
              <span>Só para {monthLabel(month)}
                <span className="block text-xs text-slate-400">{form.onlyMonth ? "Os outros meses continuam com o limite padrão." : "Vale para todos os meses."}{form.defaultLimit && form.override ? ` Padrão: ${fmt(form.defaultLimit)}.` : ""}</span>
              </span>
            </label>
            <div className="flex gap-3">
              {form.existing && <button type="button" className="btn-ghost text-red-300" data-testid="budget-delete-button" aria-label="Remover"
                onClick={(e) => setConfirm(form.override
                  ? { origin: originFrom(e), category: form.category, month, title: "Remover limite do mês", message: `Remover o limite especial de ${getCategory(form.category).label} em ${monthLabel(month)}?${form.defaultLimit ? ` Volta ao padrão de ${fmt(form.defaultLimit)}.` : ""}` }
                  : { origin: originFrom(e), category: form.category, title: "Remover orçamento", message: `Remover o limite padrão de ${getCategory(form.category).label}?` })}><Trash2 size={16} /></button>}
              <button className="btn-primary flex-1" data-testid="budget-submit-button">Salvar</button>
            </div>
          </form>
        )}
      </GlassModal>
      <ConfirmModal state={confirm} onClose={() => setConfirm(null)} onConfirm={remove} testId="budget-confirm" />
    </section>
  );
};
