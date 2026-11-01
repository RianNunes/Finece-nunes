import { useRef } from "react";

export const CategoryPicker = ({ categories, value, onChange, testId = "category-picker" }) => {
  const refs = useRef([]);
  const idx = Math.max(0, categories.findIndex((c) => c.key === value));

  const onKey = (e, i) => {
    const cols = window.innerWidth < 640 ? 3 : 5;
    const map = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: cols, ArrowUp: -cols };
    if (!(e.key in map)) return;
    e.preventDefault();
    const n = (i + map[e.key] + categories.length) % categories.length;
    onChange(categories[n].key);
    refs.current[n]?.focus();
  };

  return (
    <div role="radiogroup" aria-label="Categoria" className="grid grid-cols-3 sm:grid-cols-5 gap-2" data-testid={testId}>
      {categories.map((c, i) => {
        const Icon = c.icon;
        const active = c.key === value;
        return (
          <button
            key={c.key} type="button" role="radio" aria-checked={active} tabIndex={i === idx ? 0 : -1}
            ref={(el) => (refs.current[i] = el)} onClick={() => onChange(c.key)} onKeyDown={(e) => onKey(e, i)}
            data-testid={`${testId}-${c.key}`}
            className={`cat-chip ${active ? "is-active" : ""}`}
            style={{ "--c": c.color }}
          >
            <span className="cat-dot"><Icon size={15} /></span>
            <span className="text-[11px] leading-tight text-center">{c.label}</span>
          </button>
        );
      })}
    </div>
  );
};
