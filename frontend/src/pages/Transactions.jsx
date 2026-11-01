import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Plus, Search, Receipt } from "lucide-react";
import { api, errorMessage } from "@/lib/api";
import { useApp, useFetch } from "@/context/AppContext";
import { EXPENSE_CATEGORIES, INCOME_CATEGORIES, fmt } from "@/lib/finance";
import { MonthSwitcher, PageHeader, Empty } from "@/components/MonthSwitcher";
import { TxRow } from "@/components/TxList";
import { TransactionForm } from "@/components/TransactionForm";
import { ConfirmModal, originFrom } from "@/components/GlassModal";

export default function Transactions() {
  const { month, bump } = useApp();
  const { data: txs } = useFetch(`/transactions?month=${month}`);
  const [q, setQ] = useState("");
  const [type, setType] = useState("all");
  const [cat, setCat] = useState("all");
  const [form, setForm] = useState(null);
  const [confirm, setConfirm] = useState(null);

  const list = useMemo(() => (txs || []).filter((t) =>
    (type === "all" || t.type === type) && (cat === "all" || t.category === cat) &&
    (!q || (t.description || "").toLowerCase().includes(q.toLowerCase()))), [txs, q, type, cat]);
  const total = list.reduce((s, t) => s + (t.type === "income" ? t.amount : -t.amount), 0);

  const remove = async () => {
    try {
      await api.delete(`/transactions/${confirm.id}`);
      toast.success("Movimentação excluída"); bump();
    } catch (e) { toast.error(errorMessage(e)); }
    setConfirm(null);
  };

  return (
    <div>
      <PageHeader eyebrow="Extrato" title="Movimentações">
        <MonthSwitcher />
        <button className="btn-primary" onClick={(e) => setForm({ origin: originFrom(e) })} data-testid="new-transaction-button"><Plus size={17} /> Nova</button>
      </PageHeader>
      <section className="glass card">
        <div className="flex flex-col sm:flex-row gap-3 mb-5">
          <label className="search flex-1"><Search size={16} className="text-slate-400" /><input placeholder="Buscar por descrição" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Buscar" data-testid="tx-search-input" /></label>
          <select className="select" value={type} onChange={(e) => { setType(e.target.value); setCat("all"); }} aria-label="Tipo" data-testid="tx-filter-type">
            <option value="all">Todos os tipos</option><option value="income">Receitas</option><option value="expense">Despesas</option>
          </select>
          <select className="select" value={cat} onChange={(e) => setCat(e.target.value)} aria-label="Categoria" data-testid="tx-filter-category">
            <option value="all">Todas as categorias</option>
            {(type === "income" ? INCOME_CATEGORIES : type === "expense" ? EXPENSE_CATEGORIES : [...EXPENSE_CATEGORIES, ...INCOME_CATEGORIES]).map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
          </select>
        </div>
        <div className="flex justify-between text-xs text-slate-400 mb-2 px-1">
          <span data-testid="tx-count">{list.length} movimentações</span>
          <span className="tabular" data-testid="tx-filtered-total">Saldo filtrado: <span className={total < 0 ? "text-red-300" : "text-emerald-300"}>{fmt(total)}</span></span>
        </div>
        {txs && !list.length ? <Empty icon={Receipt} text={txs.length ? "Nada encontrado com esses filtros." : "Nenhuma movimentação neste mês. Clique em Nova para começar."} testId="tx-empty" /> : (
          <ul className="divide-y divide-white/5" data-testid="tx-list">
            {list.map((t) => <TxRow key={t.id} tx={t}
              onEdit={(e, tx) => setForm({ origin: originFrom(e), tx })}
              onDelete={(e, tx) => setConfirm({ origin: originFrom(e), id: tx.id, title: "Excluir movimentação", message: `Excluir "${tx.description || "movimentação"}" de ${fmt(tx.amount)}?` })} />)}
          </ul>
        )}
      </section>
      <TransactionForm state={form} onClose={() => setForm(null)} />
      <ConfirmModal state={confirm} onClose={() => setConfirm(null)} onConfirm={remove} testId="tx-confirm" />
    </div>
  );
}
