import { useState } from "react";
import { useApp, useFetch } from "@/context/AppContext";
import { MonthSwitcher, PageHeader } from "@/components/MonthSwitcher";
import { Budgets } from "@/components/Budgets";
import { Goals } from "@/components/Goals";
import { Recurring } from "@/components/Recurring";
import { Installments } from "@/components/Installments";
import { TransactionForm } from "@/components/TransactionForm";
import { originFrom } from "@/components/GlassModal";

export default function Planning() {
  const { month } = useApp();
  const { data: s } = useFetch(`/summary?month=${month}`);
  const [form, setForm] = useState(null);
  return (
    <div>
      <PageHeader eyebrow="Planejamento" title="Orçamentos e metas"><MonthSwitcher /></PageHeader>
      <div className="grid lg:grid-cols-2 gap-4">
        <Budgets budgets={s?.budgets} />
        <Recurring />
        <div className="lg:col-span-2"><Goals /></div>
        <div className="lg:col-span-2"><Installments onNew={(e) => setForm({ origin: originFrom(e), preset: { installments: 2, category: "compras" } })} /></div>
      </div>
      <TransactionForm state={form} onClose={() => setForm(null)} />
    </div>
  );
}
