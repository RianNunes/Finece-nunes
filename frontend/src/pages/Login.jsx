import { useState } from "react";
import { Navigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Lock } from "lucide-react";
import { useApp } from "@/context/AppContext";
import { errorMessage } from "@/lib/api";
import { Brand } from "@/components/Layout";

export default function Login() {
  const { user, login, register } = useApp();
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      if (mode === "login") await login(f.email, f.password);
      else await register(f.name, f.email, f.password);
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  return (
    <div className="min-h-screen grid lg:grid-cols-[1.1fr_1fr]">
      <div className="hidden lg:flex flex-col justify-between p-14">
        <Brand />
        <div className="rise">
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400 mb-5">Seu dinheiro, com clareza</p>
          <h1 className="font-display text-5xl xl:text-6xl font-semibold tracking-tight leading-[1.05] max-w-[560px]">
            Cada real no lugar <span className="text-gradient">certo.</span>
          </h1>
          <p className="mt-6 text-slate-400 max-w-md">Receitas, despesas, orçamentos, metas e um assistente que entende seus gastos.</p>
        </div>
        <div className="flex gap-3 text-xs text-slate-500"><Lock size={14} /> Seus dados ficam protegidos por login.</div>
      </div>
      <div className="flex items-center justify-center p-5">
        <motion.form onSubmit={submit} initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
          className="glass-strong w-full max-w-[420px] rounded-[30px] p-8 space-y-5" data-testid="auth-form">
          <div className="lg:hidden mb-2"><Brand /></div>
          <div>
            <h2 className="font-display text-2xl font-semibold">{mode === "login" ? "Entrar" : "Criar conta"}</h2>
            <p className="text-sm text-slate-400 mt-1">{mode === "login" ? "Bem-vindo de volta." : "Leva menos de um minuto."}</p>
          </div>
          {mode === "register" && (
            <label className="field"><span>Nome</span><input value={f.name} onChange={set("name")} autoComplete="name" data-testid="auth-name-input" required /></label>
          )}
          <label className="field"><span>E-mail</span><input type="email" value={f.email} onChange={set("email")} autoComplete="email" data-testid="auth-email-input" required /></label>
          <label className="field"><span>Senha</span><input type="password" value={f.password} onChange={set("password")} minLength={6} autoComplete={mode === "login" ? "current-password" : "new-password"} data-testid="auth-password-input" required /></label>
          {error && <p role="alert" className="text-sm text-red-300 bg-red-500/10 border border-red-400/20 rounded-xl px-3 py-2" data-testid="auth-error">{error}</p>}
          <button className="btn-primary w-full" disabled={busy} data-testid="auth-submit-button">{busy ? "Aguarde..." : mode === "login" ? "Entrar" : "Criar conta"}</button>
          <button type="button" className="w-full text-sm text-slate-400 hover:text-white transition-colors" data-testid="auth-toggle-mode"
            onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
            {mode === "login" ? "Não tem conta? Criar conta" : "Já tem conta? Entrar"}
          </button>
        </motion.form>
      </div>
    </div>
  );
}
