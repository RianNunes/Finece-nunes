import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Send, Bot, Trash2, Sparkles } from "lucide-react";
import { api, API_BASE, refreshSession } from "@/lib/api";
import { PageHeader } from "@/components/MonthSwitcher";

const SUGGESTIONS = ["Onde gastei mais este mês?", "Como estou na regra 50-30-20?", "Quanto gastei com restaurantes nos últimos meses?", "Dicas para economizar com base nos meus gastos"];

const md = (t) => t.split("\n").map((line, i) => {
  const parts = line.split(/(\*\*[^*]+\*\*)/g).map((p, j) => p.startsWith("**") && p.endsWith("**") ? <strong key={j}>{p.slice(2, -2)}</strong> : p);
  const bullet = /^\s*[-*•]\s/.test(line);
  return <p key={i} className={bullet ? "pl-3" : ""}>{bullet ? <>• {parts.map((p) => typeof p === "string" ? p.replace(/^\s*[-*•]\s/, "") : p)}</> : parts}</p>;
});

const post = (message) => fetch(`${API_BASE}/chat`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message }) });

export default function Assistant() {
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef(null);

  useEffect(() => { api.get("/chat/history").then((r) => setMsgs(r.data)).catch(() => {}); }, []);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [msgs]);

  const send = async (text) => {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    setInput(""); setBusy(true);
    setMsgs((m) => [...m, { role: "user", content: message }, { role: "assistant", content: "", pending: true }]);
    const append = (patch) => setMsgs((m) => { const c = [...m]; c[c.length - 1] = { ...c[c.length - 1], ...patch(c[c.length - 1]) }; return c; });
    try {
      let res = await post(message);
      if (res.status === 401) { await refreshSession(); res = await post(message); }
      if (!res.ok) throw new Error();
      const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const events = buf.split("\n\n"); buf = events.pop();
        for (const ev of events) {
          if (!ev.startsWith("data: ")) continue;
          const d = JSON.parse(ev.slice(6));
          if (d.delta) append((l) => ({ content: l.content + d.delta, pending: false }));
          if (d.error) append(() => ({ content: d.error, pending: false, error: true }));
        }
      }
    } catch {
      append(() => ({ content: "Não consegui responder agora. Tente de novo.", pending: false, error: true }));
    } finally { setBusy(false); }
  };

  const clear = async () => { await api.delete("/chat/history"); setMsgs([]); toast.success("Conversa apagada"); };

  return (
    <div className="flex flex-col h-[calc(100vh-170px)] md:h-[calc(100vh-64px)]">
      <PageHeader eyebrow="Assistente com IA" title="Pergunte sobre seus gastos">
        {!!msgs.length && <button className="btn-ghost" onClick={clear} data-testid="chat-clear-button"><Trash2 size={15} /> Limpar conversa</button>}
      </PageHeader>
      <section className="glass card flex-1 flex flex-col min-h-0 !p-0 overflow-hidden">
        <div className="flex-1 overflow-y-auto p-5 sm:p-7 space-y-4" data-testid="chat-messages" aria-live="polite">
          {!msgs.length && (
            <div className="h-full flex flex-col items-center justify-center text-center gap-5">
              <div className="empty-icon !h-14 !w-14"><Sparkles size={24} /></div>
              <p className="text-slate-300 max-w-sm">Eu leio suas movimentações, orçamentos e metas para responder. Experimente:</p>
              <div className="flex flex-wrap justify-center gap-2 max-w-xl">
                {SUGGESTIONS.map((s, i) => <button key={s} className="chip-btn" onClick={() => send(s)} data-testid={`chat-suggestion-${i}`}>{s}</button>)}
              </div>
            </div>
          )}
          {msgs.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : ""}`} data-testid={`chat-message-${m.role}`}>
              {m.role === "assistant" && <span className="cat-dot shrink-0" style={{ "--c": "#60A5FA" }}><Bot size={15} /></span>}
              <div className={`bubble ${m.role === "user" ? "bubble-user" : ""} ${m.error ? "text-red-300" : ""}`}>
                {m.pending ? <span className="typing"><i /><i /><i /></span> : md(m.content)}
              </div>
            </div>
          ))}
          <div ref={end} />
        </div>
        <form onSubmit={(e) => { e.preventDefault(); send(); }} className="p-3 sm:p-4 border-t border-white/10 flex gap-2">
          <input className="chat-input" placeholder="Ex.: onde gastei mais em outubro?" value={input} onChange={(e) => setInput(e.target.value)} maxLength={2000} aria-label="Mensagem" data-testid="chat-input" />
          <button className="btn-primary !px-4" disabled={busy || !input.trim()} aria-label="Enviar" data-testid="chat-send-button"><Send size={17} /></button>
        </form>
      </section>
    </div>
  );
}
