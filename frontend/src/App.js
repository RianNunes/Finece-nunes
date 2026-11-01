import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AppProvider, useApp } from "@/context/AppContext";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Transactions from "@/pages/Transactions";
import Planning from "@/pages/Planning";
import Assistant from "@/pages/Assistant";
import Profile from "@/pages/Profile";

const Protected = ({ children }) => {
  const { user } = useApp();
  if (user === null) return <div className="min-h-screen grid place-items-center"><div className="spinner" data-testid="app-loading" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
};

export default function App() {
  return (
    <AppProvider>
      <div className="bg-scene" aria-hidden="true"><span className="orb orb-1" /><span className="orb orb-2" /><span className="orb orb-3" /><span className="grain" /></div>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Protected><Layout /></Protected>}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/movimentacoes" element={<Transactions />} />
            <Route path="/planejamento" element={<Planning />} />
            <Route path="/assistente" element={<Assistant />} />
            <Route path="/perfil" element={<Profile />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster theme="dark" position="top-center" richColors toastOptions={{ className: "glass-toast" }} />
    </AppProvider>
  );
}
