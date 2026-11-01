import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, ArrowLeftRight, Target, Bot, UserRound, LogOut, FolderOpen } from "lucide-react";
import { useApp } from "@/context/AppContext";

export const NAV = [
  { to: "/", label: "Painel", icon: LayoutDashboard, id: "dashboard" },
  { to: "/movimentacoes", label: "Movimentações", short: "Extrato", icon: ArrowLeftRight, id: "transactions" },
  { to: "/planejamento", label: "Planejamento", short: "Planos", icon: Target, id: "planning" },
  { to: "/arquivos", label: "Arquivos", icon: FolderOpen, id: "files" },
  { to: "/assistente", label: "Assistente IA", short: "IA", icon: Bot, id: "assistant" },
  { to: "/perfil", label: "Perfil", icon: UserRound, id: "profile" },
];

export const Brand = () => (
  <div className="flex items-center gap-3">
    <div className="brand-mark">FN</div>
    <div className="leading-tight">
      <p className="font-display font-semibold text-[17px] tracking-tight">Finance Nunes</p>
      <p className="text-[11px] text-slate-400">finanças pessoais</p>
    </div>
  </div>
);

export default function Layout() {
  const { logout, user } = useApp();
  return (
    <div className="min-h-screen md:flex">
      <a href="#main" className="skip-link">Pular para o conteúdo</a>
      <aside className="hidden md:flex glass fixed inset-y-4 left-4 w-[232px] rounded-[28px] flex-col p-5 z-30" data-testid="sidebar">
        <Brand />
        <nav className="mt-10 flex flex-col gap-1" aria-label="Principal">
          {NAV.map(({ to, label, icon: Icon, id }) => (
            <NavLink key={to} to={to} end={to === "/"} data-testid={`nav-${id}`}
              className={({ isActive }) => `nav-item ${isActive ? "is-active" : ""}`}>
              <Icon size={18} /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto pt-4 border-t border-white/10">
          <p className="text-xs text-slate-400 truncate mb-2" data-testid="sidebar-user-email">{user?.email}</p>
          <button onClick={logout} className="nav-item w-full" data-testid="logout-button"><LogOut size={18} /> Sair</button>
        </div>
      </aside>
      <main id="main" className="flex-1 md:ml-[264px] px-4 sm:px-8 pt-6 pb-28 md:pb-10">
        <div className="max-w-[1360px] mx-auto">
          <div className="md:hidden mb-6"><Brand /></div>
          <Outlet />
        </div>
      </main>
      <nav className="md:hidden glass-strong fixed bottom-3 inset-x-3 rounded-[22px] z-30 grid grid-cols-6 p-1.5" aria-label="Principal" data-testid="bottom-nav">
        {NAV.map(({ to, label, short, icon: Icon, id }) => (
          <NavLink key={to} to={to} end={to === "/"} data-testid={`bottom-nav-${id}`}
            className={({ isActive }) => `bottom-item ${isActive ? "is-active" : ""}`}>
            <Icon size={19} /><span>{short || label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
