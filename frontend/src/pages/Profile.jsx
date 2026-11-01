import { useEffect, useState } from "react";
import { toast } from "sonner";
import { LogOut } from "lucide-react";
import { api, errorMessage } from "@/lib/api";
import { useApp } from "@/context/AppContext";
import { PageHeader } from "@/components/MonthSwitcher";

export default function Profile() {
  const { user, setUser, logout } = useApp();
  const [f, setF] = useState({ name: "", email: "" });
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (user) setF({ name: user.name || "", email: user.email }); }, [user]);

  const save = async (e) => {
    e.preventDefault(); setBusy(true);
    try { setUser((await api.put("/auth/me", f)).data); toast.success("Perfil salvo"); }
    catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  };
  const initials = (f.name || f.email || "?").split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div>
      <PageHeader eyebrow="Conta" title="Perfil" />
      <section className="glass card max-w-xl">
        <div className="flex items-center gap-4 mb-7">
          <div className="brand-mark !h-14 !w-14 !text-lg" data-testid="profile-initials">{initials}</div>
          <div><p className="font-display text-lg font-semibold" data-testid="profile-name">{user?.name || "Sem nome"}</p><p className="text-sm text-slate-400">{user?.email}</p></div>
        </div>
        <form onSubmit={save} className="space-y-4">
          <label className="field"><span>Nome</span><input value={f.name} maxLength={80} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="profile-name-input" required /></label>
          <label className="field"><span>E-mail</span><input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="profile-email-input" required /></label>
          <div className="flex gap-3 pt-2">
            <button className="btn-primary flex-1" disabled={busy} data-testid="profile-save-button">{busy ? "Salvando..." : "Salvar alterações"}</button>
            <button type="button" className="btn-ghost md:hidden" onClick={logout} data-testid="profile-logout-button"><LogOut size={16} /> Sair</button>
          </div>
        </form>
      </section>
    </div>
  );
}
