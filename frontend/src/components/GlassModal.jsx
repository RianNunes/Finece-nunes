import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";

const useIsMobile = () => {
  const [m, setM] = useState(() => window.innerWidth < 640);
  useEffect(() => {
    const on = () => setM(window.innerWidth < 640);
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);
  return m;
};

export const originFrom = (e) => (e?.currentTarget ? e.currentTarget.getBoundingClientRect() : null);

export const GlassModal = ({ open, onClose, origin, title, children, testId = "modal", wide = false }) => {
  const reduce = useReducedMotion();
  const mobile = useIsMobile();
  const panel = useRef(null);

  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    setTimeout(() => panel.current?.querySelector("input,button,select,textarea")?.focus(), 60);
    return () => { window.removeEventListener("keydown", onKey); prev?.focus?.(); };
  }, [open, onClose]);

  const off = origin
    ? { x: origin.left + origin.width / 2 - window.innerWidth / 2, y: origin.top + origin.height / 2 - window.innerHeight / 2 }
    : { x: 0, y: 24 };
  const v = reduce
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 } }
    : mobile
    ? { initial: { y: "100%" }, animate: { y: 0 }, exit: { y: "100%" } }
    : { initial: { opacity: 0, scale: 0.15, ...off }, animate: { opacity: 1, scale: 1, x: 0, y: 0 }, exit: { opacity: 0, scale: 0.15, ...off } };

  return createPortal(
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-6"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          <div className="absolute inset-0 bg-[#020617]/70 backdrop-blur-sm" onClick={onClose} data-testid={`${testId}-overlay`} />
          <motion.div
            ref={panel} role="dialog" aria-modal="true" aria-label={title} data-testid={testId}
            {...v}
            transition={reduce ? { duration: 0.15 } : { type: "spring", damping: 26, stiffness: 300 }}
            className={`glass-strong relative w-full ${wide ? "sm:max-w-xl" : "sm:max-w-md"} max-h-[92vh] overflow-y-auto rounded-t-[28px] sm:rounded-[28px] p-6 sm:p-7`}
          >
            <div className="sm:hidden mx-auto -mt-2 mb-4 h-1.5 w-10 rounded-full bg-white/20" />
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-display text-xl font-semibold tracking-tight">{title}</h2>
              <button onClick={onClose} aria-label="Fechar" data-testid={`${testId}-close`} className="icon-btn"><X size={18} /></button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  );
};

export const ConfirmModal = ({ state, onClose, onConfirm, testId = "confirm-modal" }) => (
  <GlassModal open={!!state} onClose={onClose} origin={state?.origin} title={state?.title || "Confirmar"} testId={testId}>
    <p className="text-sm text-slate-300 mb-6">{state?.message}</p>
    <div className="flex gap-3 justify-end">
      <button className="btn-ghost" onClick={onClose} data-testid={`${testId}-cancel`}>Cancelar</button>
      <button className="btn-danger" onClick={onConfirm} data-testid={`${testId}-confirm`}>Excluir</button>
    </div>
  </GlassModal>
);
