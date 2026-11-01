import {
  Home, ShoppingCart, Car, HeartPulse, Zap, GraduationCap, Gamepad2, UtensilsCrossed, ShoppingBag,
  Tv, Plane, Sparkles, CreditCard, PiggyBank, CircleEllipsis, Briefcase, Laptop, TrendingUp, Gift,
} from "lucide-react";

export const GROUPS = {
  needs: { label: "Necessidades", pct: 50, color: "#60A5FA" },
  wants: { label: "Desejos", pct: 30, color: "#F472B6" },
  savings: { label: "Dívidas e poupança", pct: 20, color: "#34D399" },
  other: { label: "Outros", color: "#94A3B8" },
};

export const EXPENSE_CATEGORIES = [
  { key: "moradia", label: "Moradia", group: "needs", color: "#60A5FA", icon: Home },
  { key: "mercado", label: "Mercado", group: "needs", color: "#38BDF8", icon: ShoppingCart },
  { key: "transporte", label: "Transporte", group: "needs", color: "#818CF8", icon: Car },
  { key: "saude", label: "Saúde", group: "needs", color: "#2DD4BF", icon: HeartPulse },
  { key: "contas", label: "Contas da casa", group: "needs", color: "#22D3EE", icon: Zap },
  { key: "educacao", label: "Educação", group: "needs", color: "#A5B4FC", icon: GraduationCap },
  { key: "lazer", label: "Lazer", group: "wants", color: "#F472B6", icon: Gamepad2 },
  { key: "restaurantes", label: "Restaurantes", group: "wants", color: "#FB923C", icon: UtensilsCrossed },
  { key: "compras", label: "Compras", group: "wants", color: "#FBBF24", icon: ShoppingBag },
  { key: "assinaturas", label: "Assinaturas", group: "wants", color: "#C084FC", icon: Tv },
  { key: "viagens", label: "Viagens", group: "wants", color: "#F9A8D4", icon: Plane },
  { key: "cuidados", label: "Cuidados pessoais", group: "wants", color: "#FDA4AF", icon: Sparkles },
  { key: "dividas", label: "Dívidas", group: "savings", color: "#F87171", icon: CreditCard },
  { key: "investimentos", label: "Investimentos", group: "savings", color: "#34D399", icon: PiggyBank },
  { key: "outros", label: "Outros", group: "other", color: "#94A3B8", icon: CircleEllipsis },
];

export const INCOME_CATEGORIES = [
  { key: "salario", label: "Salário", color: "#34D399", icon: Briefcase },
  { key: "freelance", label: "Freelance", color: "#6EE7B7", icon: Laptop },
  { key: "rendimentos", label: "Rendimentos", color: "#5EEAD4", icon: TrendingUp },
  { key: "outras_receitas", label: "Outras receitas", color: "#A7F3D0", icon: Gift },
];

const ALL = [...EXPENSE_CATEGORIES, ...INCOME_CATEGORIES];
export const getCategory = (key) => ALL.find((c) => c.key === key) || EXPENSE_CATEGORIES[14];

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
export const fmt = (v) => brl.format(Number(v) || 0);

export const currentMonth = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};
export const today = () => {
  const d = new Date();
  return `${currentMonth()}-${String(d.getDate()).padStart(2, "0")}`;
};
export const shiftMonth = (m, n) => {
  const [y, mo] = m.split("-").map(Number);
  const d = new Date(y, mo - 1 + n, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};
export const monthLabel = (m, short = false) => {
  const [y, mo] = m.split("-").map(Number);
  const s = new Date(y, mo - 1, 1).toLocaleDateString("pt-BR", short ? { month: "short" } : { month: "long", year: "numeric" });
  return s.charAt(0).toUpperCase() + s.slice(1).replace(".", "");
};
export const dateLabel = (d) => {
  const [y, m, day] = d.split("-").map(Number);
  return new Date(y, m - 1, day).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }).replace(".", "");
};
export const parseAmount = (s) => {
  const v = String(s).trim().replace(/\s|R\$/g, "");
  const n = v.includes(",") ? Number(v.replace(/\./g, "").replace(",", ".")) : Number(v);
  return Number.isFinite(n) ? n : NaN;
};
export const progressColor = (pct) => (pct > 100 ? "var(--red)" : pct > 80 ? "var(--amber)" : "var(--green)");
