import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts";
import { PieChart as PieIcon, BarChart3 } from "lucide-react";
import { fmt, getCategory, monthLabel, GROUPS } from "@/lib/finance";
import { Empty } from "@/components/MonthSwitcher";

const tip = { background: "rgba(10,18,40,.92)", border: "1px solid rgba(255,255,255,.12)", borderRadius: 14, color: "#e2e8f0", fontSize: 12 };

export const CategoryDonut = ({ data, total }) => {
  if (!data?.length) return <Empty icon={PieIcon} text="Sem despesas neste mês. Lance uma despesa para ver o gráfico." testId="donut-empty" />;
  const rows = data.map((d) => ({ ...d, ...getCategory(d.category) }));
  return (
    <div className="grid sm:grid-cols-[200px_1fr] gap-6 items-center" data-testid="category-donut">
      <div className="relative h-[200px]">
        <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 200 }}>
          <PieChart>
            <Pie data={rows} dataKey="amount" nameKey="label" innerRadius={62} outerRadius={92} paddingAngle={2} stroke="none">
              {rows.map((r) => <Cell key={r.key} fill={r.color} />)}
            </Pie>
            <Tooltip contentStyle={tip} formatter={(v) => fmt(v)} itemStyle={{ color: "#e2e8f0" }} />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-[11px] text-slate-400">Total</span>
          <span className="font-display font-semibold tabular" data-testid="donut-total">{fmt(total)}</span>
        </div>
      </div>
      <ul className="space-y-2.5">
        {rows.map((r) => (
          <li key={r.key} className="flex items-center gap-3 text-sm" data-testid={`donut-legend-${r.key}`}>
            <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: r.color }} />
            <span className="flex-1 truncate">{r.label} <span className="text-[10px] text-slate-500 ml-1">{GROUPS[r.group]?.label}</span></span>
            <span className="tabular text-slate-300">{fmt(r.amount)}</span>
            <span className="tabular text-slate-500 w-11 text-right">{total ? Math.round((r.amount / total) * 100) : 0}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

export const HistoryChart = ({ data }) => {
  if (!data?.some((d) => d.income || d.expense)) return <Empty icon={BarChart3} text="O comparativo aparece assim que houver lançamentos." testId="history-empty" />;
  const rows = data.map((d) => ({ ...d, name: monthLabel(d.month, true) }));
  return (
    <div className="h-[240px]" data-testid="history-chart">
      <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 320, height: 200 }}>
        <BarChart data={rows} barGap={4}>
          <CartesianGrid vertical={false} stroke="rgba(255,255,255,.06)" />
          <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} width={56}
            tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k` : v)} />
          <Tooltip contentStyle={tip} formatter={(v) => fmt(v)} cursor={{ fill: "rgba(255,255,255,.04)" }} />
          <Bar dataKey="income" name="Receitas" fill="#34D399" radius={[6, 6, 0, 0]} maxBarSize={22} />
          <Bar dataKey="expense" name="Despesas" fill="#F87171" radius={[6, 6, 0, 0]} maxBarSize={22} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
