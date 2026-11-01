import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, errorMessage } from "@/lib/api";
import { EXPENSE_CATEGORIES, INCOME_CATEGORIES, parseAmount, today } from "@/lib/finance";
import { GlassModal } from "@/components/GlassModal";
import { CategoryPicker } from "@/components/CategoryPicker";
import { useApp } from "@/context/AppContext";

const empty = (preset = {}) => ({ type: "expense", amount: "", description: "", date: today(), category: "mercado", installments: 1, ...preset });

export const TransactionForm = ({ state, onClose }) => {
  const { bump } = useApp();
  const editing = state?.tx && !state.tx.recurring;
  const [f, setF] = useState(empty());
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!state) return;
    const t = state.tx;
    setF(t ? { ...empty(), ...t, amount: String(t.amount).replace(".", ",") } : empty(state.preset));
  }, [state]);

  const set = (k) => (v) => setF((p) => ({ ...p, [k]: v?.target ? v.target.value : v }));
  const setType = (type) => setF((p) => ({ ...p, type, category: type === "income" ? "salario" : "mercado", installments: 1 }));
  const cats = f.type === "income" ? INCOME_CATEGORIES : EXPENSE_CATEGORIES;
  const n = Number(f.installments) || 1;
  const amount = parseAmount(f.amount);

  const submit = async (e) => {
    e.preventDefault();
    if (!(amount > 0)) return toast.error("Informe um valor maior que zero");
    setSaving(true);
    try {
      if (!editing && f.type === "expense" && n > 1) {
        await api.post("/installments", { description: f.description || "Compra parcelada", total_amount: amount, installments: n, category: f.category, start_date: f.date });
        toast.success(`Compra em ${n}x salva`);
      } else {
        const body = { type: f.type, amount, description: f.description, date: f.date, category: f.category };
        if (editing) await api.put(`/transactions/${state.tx.id}`, body);
        else await api.post("/transactions", body);
        toast.success(editing ? "Movimentação atualizada" : "Movimentação salva");
      }
      bump();
      onClose();
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <GlassModal open={!!state} onClose={onClose} origin={state?.origin} wide testId="tx-modal"
      title={editing ? "Editar movimentação" : "Nova movimentação"}>
      <form onSubmit={submit} className="space-y-5">
        <div className="seg" role="tablist" aria-label="Tipo">
          {[["expense", "Despesa"], ["income", "Receita"]].map(([k, l]) => (
            <button type="button" key={k} role="tab" aria-selected={f.type === k} data-testid={`tx-type-${k}`}
              className={`seg-btn ${f.type === k ? (k === "income" ? "on-green" : "on-red") : ""}`} onClick={() => setType(k)}>{l}</button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <label className="field col-span-2 sm:col-span-1"><span>Valor (R$)</span>
            <input inputMode="decimal" placeholder="0,00" value={f.amount} onChange={set("amount")} data-testid="tx-amount-input" required />
          </label>
          <label className="field col-span-2 sm:col-span-1"><span>{n > 1 ? "1ª parcela em" : "Data"}</span>
            <input type="date" value={f.date} onChange={set("date")} data-testid="tx-date-input" required />
          </label>
          <label className="field col-span-2"><span>Descrição</span>
            <input placeholder="Ex.: Supermercado do mês" maxLength={200} value={f.description} onChange={set("description")} data-testid="tx-description-input" />
          </label>
        </div>
        <div>
          <p className="field-label mb-2">Categoria</p>
          <CategoryPicker categories={cats} value={f.category} onChange={set("category")} testId="tx-category" />
        </div>
        {!editing && f.type === "expense" && (
          <label className="field"><span>Parcelas</span>
            <select value={f.installments} onChange={set("installments")} data-testid="tx-installments-select">
              {Array.from({ length: 24 }, (_, i) => i + 1).map((i) => <option key={i} value={i}>{i === 1 ? "À vista" : `${i}x`}</option>)}
            </select>
            {n > 1 && amount > 0 && <small className="text-slate-400 mt-1" data-testid="tx-installment-preview">{n}x de {(amount / n).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</small>}
          </label>
        )}
        <button className="btn-primary w-full" disabled={saving} data-testid="tx-submit-button">{saving ? "Salvando..." : "Salvar"}</button>
      </form>
    </GlassModal>
  );
};
