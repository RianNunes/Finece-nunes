import { useState } from "react";
import { toast } from "sonner";
import { Plus, Flag, Pencil, Trash2, PiggyBank } from "lucide-react";
import { api, errorMessage } from "@/lib/api";
import { dateLabel, fmt, parseAmount } from "@/lib/finance";
import { GlassModal, ConfirmModal, originFrom } from "@/components/GlassModal";
import { Empty } from "@/components/MonthSwitcher";
import { useApp, useFetch } from "@/context/AppContext";

const GoalCard = ({ g, onContribute, onEdit, onDelete }) => {
  const pct = Math.min(100, (g.saved / g.target) * 100);
  const done = g.saved >= g.target;
  return (
    <div className="goal" data-testid={`goal-${g.id}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium truncate" data-testid={`goal-name-${g.id}`}>{g.name}</p>
          <p className="text-xs text-slate-400">{g.deadline ? `até ${dateLabel(g.deadline)} ${g.deadline.slice(0, 4)}` : "sem prazo"}</p>
        </div>
        <div className="flex gap-1">
          <button className="icon-btn" aria-label="Editar meta" onClick={onEdit} data-testid={`goal-edit-${g.id}`}><Pencil size={14} /></button>
          <button className="icon-btn" aria-label="Excluir meta" onClick={onDelete} data-testid={`goal-delete-${g.id}`}><Trash2 size={14} /></button>
        </div>
      </div>
      <p className="mt-3 tabular text-sm"><span className="font-display text-lg font-semibold" data-testid={`goal-saved-${g.id}`}>{fmt(g.saved)}</span> <span className="text-slate-400">de {fmt(g.target)}</span></p>
      <div className="bar mt-2"><div className="bar-fill" style={{ width: `${pct}%`, background: done ? "var(--green)" : "var(--blue)" }} /></div>
      <div className="flex items-center justify-between mt-3">
        <span className="text-xs text-slate-400 tabular">{done ? "Meta concluída!" : `${Math.round(pct)}% · faltam ${fmt(g.target - g.saved)}`}</span>
        <button className="chip-btn" onClick={onContribute} data-testid={`goal-contribute-${g.id}`}><PiggyBank size={14} /> Aportar</button>
      </div>
    </div>
  );
};

export const Goals = ({ limit }) => {
  const { bump } = useApp();
  const { data: goals } = useFetch("/goals");
  const [form, setForm] = useState(null);
  const [contrib, setContrib] = useState(null);
  const [confirm, setConfirm] = useState(null);

  const save = async (e) => {
    e.preventDefault();
    const target = parseAmount(form.target), saved = parseAmount(form.saved || "0");
    if (!(target > 0) || !(saved >= 0)) return toast.error("Verifique os valores");
    const body = { name: form.name, target, saved, deadline: form.deadline || null };
    try {
      if (form.id) await api.put(`/goals/${form.id}`, body); else await api.post("/goals", body);
      toast.success("Meta salva"); setForm(null); bump();
    } catch (err) { toast.error(errorMessage(err)); }
  };
  const addContrib = async (e) => {
    e.preventDefault();
    const amount = parseAmount(contrib.amount);
    if (!amount) return toast.error("Informe um valor");
    try {
      await api.post(`/goals/${contrib.id}/contribute`, { amount: contrib.withdraw ? -amount : amount });
      toast.success(contrib.withdraw ? "Retirada registrada" : "Aporte registrado"); setContrib(null); bump();
    } catch (err) { toast.error(errorMessage(err)); }
  };
  const remove = async () => {
    await api.delete(`/goals/${confirm.id}`).catch((e) => toast.error(errorMessage(e)));
    toast.success("Meta excluída"); setConfirm(null); bump();
  };
  const list = limit ? goals?.slice(0, limit) : goals;

  return (
    <section className="glass card" data-testid="goals-card">
      <div className="card-head">
        <h2 className="card-title">Metas financeiras</h2>
        <button className="chip-btn" data-testid="goal-add-button" onClick={(e) => setForm({ origin: originFrom(e), name: "", target: "", saved: "", deadline: "" })}><Plus size={15} /> Meta</button>
      </div>
      {goals && !goals.length ? <Empty icon={Flag} text="Crie uma meta, como reserva de emergência ou viagem." testId="goals-empty" /> : (
        <div className="grid sm:grid-cols-2 gap-3">
          {list?.map((g) => (
            <GoalCard key={g.id} g={g}
              onContribute={(e) => setContrib({ origin: originFrom(e), id: g.id, name: g.name, amount: "", withdraw: false })}
              onEdit={(e) => setForm({ origin: originFrom(e), ...g, target: String(g.target).replace(".", ","), saved: String(g.saved).replace(".", ","), deadline: g.deadline || "" })}
              onDelete={(e) => setConfirm({ origin: originFrom(e), id: g.id, title: "Excluir meta", message: `Excluir a meta "${g.name}"?` })} />
          ))}
        </div>
      )}
      <GlassModal open={!!form} onClose={() => setForm(null)} origin={form?.origin} title={form?.id ? "Editar meta" : "Nova meta"} testId="goal-modal">
        {form && (
          <form onSubmit={save} className="space-y-4">
            <label className="field"><span>Nome</span><input value={form.name} maxLength={120} placeholder="Ex.: Reserva de emergência" onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="goal-name-input" required /></label>
            <div className="grid grid-cols-2 gap-3">
              <label className="field"><span>Valor desejado</span><input inputMode="decimal" placeholder="0,00" value={form.target} onChange={(e) => setForm({ ...form, target: e.target.value })} data-testid="goal-target-input" required /></label>
              <label className="field"><span>Já guardado</span><input inputMode="decimal" placeholder="0,00" value={form.saved} onChange={(e) => setForm({ ...form, saved: e.target.value })} data-testid="goal-saved-input" /></label>
            </div>
            <label className="field"><span>Data (opcional)</span><input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} data-testid="goal-deadline-input" /></label>
            <button className="btn-primary w-full" data-testid="goal-submit-button">Salvar</button>
          </form>
        )}
      </GlassModal>
      <GlassModal open={!!contrib} onClose={() => setContrib(null)} origin={contrib?.origin} title={contrib?.name || "Aporte"} testId="contrib-modal">
        {contrib && (
          <form onSubmit={addContrib} className="space-y-4">
            <div className="seg">
              <button type="button" className={`seg-btn ${!contrib.withdraw ? "on-green" : ""}`} onClick={() => setContrib({ ...contrib, withdraw: false })} data-testid="contrib-add-tab">Aportar</button>
              <button type="button" className={`seg-btn ${contrib.withdraw ? "on-red" : ""}`} onClick={() => setContrib({ ...contrib, withdraw: true })} data-testid="contrib-withdraw-tab">Retirar</button>
            </div>
            <label className="field"><span>Valor (R$)</span><input inputMode="decimal" placeholder="0,00" value={contrib.amount} onChange={(e) => setContrib({ ...contrib, amount: e.target.value })} data-testid="contrib-amount-input" required /></label>
            <button className="btn-primary w-full" data-testid="contrib-submit-button">Confirmar</button>
          </form>
        )}
      </GlassModal>
      <ConfirmModal state={confirm} onClose={() => setConfirm(null)} onConfirm={remove} testId="goal-confirm" />
    </section>
  );
};
