import { ChevronLeft, ChevronRight } from "lucide-react";
import { useApp } from "@/context/AppContext";
import { currentMonth, monthLabel, shiftMonth } from "@/lib/finance";

export const MonthSwitcher = () => {
  const { month, setMonth } = useApp();
  return (
    <div className="glass inline-flex items-center rounded-full p-1" data-testid="month-switcher">
      <button className="icon-btn" aria-label="Mês anterior" onClick={() => setMonth(shiftMonth(month, -1))} data-testid="month-prev"><ChevronLeft size={18} /></button>
      <button className="px-3 text-sm font-medium min-w-[150px] text-center" onClick={() => setMonth(currentMonth())}
        title="Voltar para o mês atual" data-testid="month-label">{monthLabel(month)}</button>
      <button className="icon-btn" aria-label="Próximo mês" onClick={() => setMonth(shiftMonth(month, 1))} data-testid="month-next"><ChevronRight size={18} /></button>
    </div>
  );
};

export const PageHeader = ({ eyebrow, title, children }) => (
  <header className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 mb-8 rise">
    <div>
      {eyebrow && <p className="text-xs uppercase tracking-[0.2em] text-slate-400 mb-2">{eyebrow}</p>}
      <h1 className="font-display text-3xl sm:text-4xl lg:text-5xl font-semibold tracking-tight" data-testid="page-title">{title}</h1>
    </div>
    <div className="flex flex-wrap items-center gap-3">{children}</div>
  </header>
);

export const Empty = ({ icon: Icon, text, testId }) => (
  <div className="flex flex-col items-center justify-center text-center py-10 text-slate-400" data-testid={testId}>
    {Icon && <div className="empty-icon mb-3"><Icon size={22} /></div>}
    <p className="text-sm max-w-[260px]">{text}</p>
  </div>
);
