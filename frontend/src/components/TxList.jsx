import { Pencil, Trash2, Repeat, Layers } from "lucide-react";
import { dateLabel, fmt, getCategory } from "@/lib/finance";

export const TxRow = ({ tx, onEdit, onDelete }) => {
  const c = getCategory(tx.category);
  const Icon = c.icon;
  const inc = tx.type === "income";
  return (
    <li className="row group" data-testid={`tx-row-${tx.id}`}>
      <span className="cat-dot" style={{ "--c": c.color }}><Icon size={15} /></span>
      <div className="flex-1 min-w-0">
        <p className="text-sm truncate">{tx.description || c.label}</p>
        <p className="text-xs text-slate-400 flex items-center gap-1.5">
          {dateLabel(tx.date)} · {c.label}
          {tx.recurring && <span className="tag"><Repeat size={10} /> recorrente</span>}
          {tx.installment_no && <span className="tag"><Layers size={10} /> {tx.installment_no}/{tx.installment_total}</span>}
        </p>
      </div>
      <span className={`tabular text-sm font-medium ${inc ? "text-emerald-300" : "text-red-300"}`} data-testid={`tx-amount-${tx.id}`}>{inc ? "+" : "-"}{fmt(tx.amount)}</span>
      {onEdit && !tx.recurring && (
        <div className="flex gap-1 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-within:opacity-100 transition-opacity">
          <button className="icon-btn" aria-label="Editar" onClick={(e) => onEdit(e, tx)} data-testid={`tx-edit-${tx.id}`}><Pencil size={14} /></button>
          <button className="icon-btn" aria-label="Excluir" onClick={(e) => onDelete(e, tx)} data-testid={`tx-delete-${tx.id}`}><Trash2 size={14} /></button>
        </div>
      )}
    </li>
  );
};
