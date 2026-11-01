import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, TrendingUp, TrendingDown, Scale, Receipt } from "lucide-react";
import { useApp, useFetch } from "@/context/AppContext";
import { fmt, GROUPS, progressColor } from "@/lib/finance";
import { MonthSwitcher, PageHeader, Empty } from "@/components/MonthSwitcher";
import { CategoryDonut, HistoryChart } from "@/components/Charts";
import { Budgets } from "@/components/Budgets";
import { Goals } from "@/components/Goals";
import { TxRow } from "@/components/TxList";
import { TransactionForm } from "@/components/TransactionForm";
import { originFrom } from "@/components/GlassModal";

const greeting = () => { const h = new Date().getHours(); return h < 12 ? "Bom dia" : h < 18 ? "Boa tarde" : "Boa noite"; };

const Stat = ({ label, value, icon: Icon, tone, testId, delay }) => (
  <div className="glass card stat rise" style={{ animationDelay: `${delay}ms`, "--tone": tone }} data-testid={testId}>
    <div className="flex items-center justify-between"><span className="text-sm text-slate-400">{label}</span><span className="stat-icon"><Icon size={16} /></span></div>
    <p className="font-display text-2xl sm:text-[28px] font-semibold tabular mt-3" data-testid={`${testId}-value`}>{fmt(value)}</p>
  </div>
);

const Rule = ({ rule, income }) => (
  <section className="glass card" data-testid="rule-card">
    <div className="card-head"><h2 className="card-title">Regra 50-30-20</h2><span className="text-xs text-slate-400">sobre {fmt(income)}</span></div>
    {!income ? <Empty icon={Scale} text="Lance suas receitas do mês para calcular as metas da regra." testId="rule-empty" /> : (
      <div className="space-y-5">
        {["needs", "wants", "savings"].map((k) => {
          const r = rule[k]; const pct = r.target ? (r.spent / r.target) * 100 : 0;
          return (
            <div key={k} data-testid={`rule-${k}`}>
              <div className="flex justify-between text-sm mb-1.5"><span>{GROUPS[k].label} <span className="text-slate-500">{r.pct}%</span></span>
                <span className="tabular text-slate-400"><span className="text-slate-100">{fmt(r.spent)}</span> / {fmt(r.target)}</span></div>
              <div className="bar"><div className="bar-fill" style={{ width: `${Math.min(pct, 100)}%`, background: k === "savings" ? GROUPS.savings.color : progressColor(pct) }} /></div>
            </div>
          );
        })}
        <p className="text-xs text-slate-500">Em "Dívidas e poupança", quanto mais perto de 100%, melhor.</p>
      </div>
    )}
  </section>
);

export default function Dashboard() {
  const { user, month } = useApp();
  const { data: s } = useFetch(`/summary?month=${month}`);
  const { data: txs } = useFetch(`/transactions?month=${month}`);
  const [form, setForm] = useState(null);
  const name = (user?.name || "").split(" ")[0];

  return (
    <div>
      <PageHeader eyebrow={`${greeting()}${name ? `, ${name}` : ""}`} title="Resumo do mês">
        <MonthSwitcher />
        <button className="btn-primary" onClick={(e) => setForm({ origin: originFrom(e) })} data-testid="new-transaction-button"><Plus size={17} /> Nova movimentação</button>
      </PageHeader>
      <div className="grid sm:grid-cols-3 gap-4 mb-4">
        <Stat label="Receitas" value={s?.income} icon={TrendingUp} tone="var(--green)" testId="stat-income" delay={0} />
        <Stat label="Despesas" value={s?.expense} icon={TrendingDown} tone="var(--red)" testId="stat-expense" delay={80} />
        <Stat label="Saldo" value={s?.balance} icon={Scale} tone={(s?.balance ?? 0) < 0 ? "var(--red)" : "var(--blue)"} testId="stat-balance" delay={160} />
      </div>
      <div className="grid lg:grid-cols-5 gap-4">
        <section className="glass card lg:col-span-3 rise" style={{ animationDelay: "200ms" }}>
          <div className="card-head"><h2 className="card-title">Despesas por categoria</h2></div>
          <CategoryDonut data={s?.by_category} total={s?.expense} />
        </section>
        <div className="lg:col-span-2 rise" style={{ animationDelay: "260ms" }}>{s && <Rule rule={s.rule} income={s.income} />}</div>
        <section className="glass card lg:col-span-3">
          <div className="card-head"><h2 className="card-title">Receitas x Despesas</h2><span className="text-xs text-slate-400">últimos 6 meses</span></div>
          <HistoryChart data={s?.history} />
        </section>
        <div className="lg:col-span-2"><Budgets budgets={s?.budgets} /></div>
        <section className="glass card lg:col-span-3" data-testid="recent-card">
          <div className="card-head"><h2 className="card-title">Últimas movimentações</h2><Link to="/movimentacoes" className="text-xs text-sky-300 hover:underline" data-testid="see-all-link">Ver todas</Link></div>
          {txs && !txs.length ? <Empty icon={Receipt} text="Nenhuma movimentação neste mês ainda." testId="recent-empty" /> :
            <ul className="divide-y divide-white/5">{txs?.slice(0, 6).map((t) => <TxRow key={t.id} tx={t} />)}</ul>}
        </section>
        <div className="lg:col-span-2"><Goals limit={2} /></div>
      </div>
      <TransactionForm state={form} onClose={() => setForm(null)} />
    </div>
  );
}
