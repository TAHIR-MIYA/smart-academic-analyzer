import { FileText, LayoutDashboard, Menu, UploadCloud, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/api.js";
import { useApi } from "../hooks/useApi.js";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/upload", label: "Upload", icon: UploadCloud },
  { to: "/documents", label: "Documents", icon: FileText },
];

function SystemStatus() {
  const { data: health, error, loading } = useApi(api.health, []);
  if (loading) return <p className="text-xs text-slate-300">Checking the API</p>;
  if (error) {
    return (
      <div className="text-xs">
        <p className="font-semibold text-red-200">API not reachable</p>
        <p className="mt-1 text-slate-300">Start it with: uvicorn app.main:app --reload</p>
      </div>
    );
  }
  const modelReady = health.model?.trained;
  const nlpReady = health.nlp_resources?.ready;
  return (
    <div className="space-y-2 text-xs text-slate-300">
      <p>
        <span className="font-semibold text-white">API connected</span>
        <br />
        Version {health.version}
      </p>
      <p className={modelReady ? "" : "text-amber-200"}>
        {modelReady ? "Classifier trained" : "Classifier not trained"}
        {!modelReady && (
          <>
            <br />
            Run: python -m app.ml.train
          </>
        )}
      </p>
      {!nlpReady && (
        <p className="text-amber-200">
          Language data missing
          <br />
          Run: python -m scripts.setup_nlp
        </p>
      )}
    </div>
  );
}

export default function Layout() {
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen md:flex">
      <a
        href="#main"
        className="sr-only z-50 bg-paper-raised px-3 py-2 focus:not-sr-only focus:fixed focus:left-2 focus:top-2"
      >
        Skip to content
      </a>

      <header className="flex items-center justify-between bg-ink px-4 py-3 text-white md:hidden">
        <span className="font-serif text-lg font-semibold">Academic Document Analyzer</span>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-controls="sidebar"
          aria-label={open ? "Close menu" : "Open menu"}
          className="rounded p-1 hover:bg-ink-soft"
        >
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </header>

      <aside
        id="sidebar"
        className={`${open ? "flex" : "hidden"} flex-col justify-between bg-ink px-5 py-6 text-slate-100 md:sticky md:top-0 md:flex md:h-screen md:w-60 md:shrink-0`}
      >
        <div>
          <div className="mb-8 hidden md:block">
            <p className="font-serif text-xl font-semibold leading-snug text-white">
              Academic
              <br />
              Document Analyzer
            </p>
            <p className="mt-1 text-xs text-slate-300">NLP mini project</p>
          </div>
          <nav aria-label="Main">
            <ul className="space-y-1">
              {NAV.map(({ to, label, icon: Icon, end }) => (
                <li key={to}>
                  <NavLink
                    to={to}
                    end={end}
                    onClick={() => setOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded px-3 py-2 text-sm font-medium ${
                        isActive ? "bg-white text-ink" : "text-slate-100 hover:bg-ink-soft"
                      }`
                    }
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>
        </div>
        <div className="mt-8 border-t border-ink-soft pt-4">
          <SystemStatus />
        </div>
      </aside>

      <main id="main" className="min-w-0 flex-1 px-5 py-8 md:px-10 md:py-10">
        <div className="mx-auto max-w-5xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
