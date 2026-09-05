import React, { useState } from "react";
import { AnomalyDashboardView } from "./components/dashboard/AnomalyDashboardView";
import { LiveInvestigationRoom } from "./components/investigation/LiveInvestigationRoom";
import { ApprovalCenterView } from "./components/approval/ApprovalCenterView";
import { KillSwitchPanel } from "./components/killswitch/KillSwitchPanel";
import {
  TrendingDown,
  Radio,
  ShieldCheck,
  AlertOctagon,
  Zap,
  Activity,
  CheckCircle2,
} from "lucide-react";

export type ActiveTab = "anomalies" | "investigation" | "approvals" | "killswitch";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("anomalies");

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Skip to content link for accessibility (WCAG 2.2 AA) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-4 focus:py-2 focus:bg-indigo-600 focus:text-white focus:rounded-md focus:shadow-lg"
      >
        Skip to main content
      </a>

      {/* App Header */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-base tracking-tight text-white">
                  RevPilot AI
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase font-mono">
                  v1.0.0-rc1
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono">
                Autonomous Revenue Intelligence & Governance
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav aria-label="Main Navigation" className="hidden md:flex items-center gap-1.5">
            <button
              onClick={() => setActiveTab("anomalies")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === "anomalies"
                  ? "bg-slate-800 text-indigo-400 border border-indigo-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent"
              }`}
            >
              <TrendingDown className="w-3.5 h-3.5" />
              Anomalies & Analytics
            </button>

            <button
              onClick={() => setActiveTab("investigation")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === "investigation"
                  ? "bg-slate-800 text-indigo-400 border border-indigo-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent"
              }`}
            >
              <Radio className="w-3.5 h-3.5 animate-pulse text-emerald-400" />
              Live Investigation Room
            </button>

            <button
              onClick={() => setActiveTab("approvals")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === "approvals"
                  ? "bg-slate-800 text-indigo-400 border border-indigo-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 border border-transparent"
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
              Approval Center
            </button>

            <button
              onClick={() => setActiveTab("killswitch")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                activeTab === "killswitch"
                  ? "bg-rose-950/60 text-rose-300 border border-rose-500/50 shadow-sm"
                  : "text-rose-400/70 hover:text-rose-300 hover:bg-rose-950/30 border border-transparent"
              }`}
            >
              <AlertOctagon className="w-3.5 h-3.5 text-rose-400" />
              Safety Controls
            </button>
          </nav>

          {/* Principal & Tenant Badges */}
          <div className="flex items-center gap-2.5">
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-800/90 text-slate-300 border border-slate-700">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              tnt_dev_001
            </span>
            <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              Human Operator (Tier 3)
            </span>
          </div>
        </div>

        {/* Mobile Navigation bar */}
        <div className="md:hidden flex items-center justify-around border-t border-slate-800 px-2 py-1.5 overflow-x-auto text-[11px]">
          <button
            onClick={() => setActiveTab("anomalies")}
            className={`px-2.5 py-1 rounded ${activeTab === "anomalies" ? "text-indigo-400 font-bold" : "text-slate-400"}`}
          >
            Anomalies
          </button>
          <button
            onClick={() => setActiveTab("investigation")}
            className={`px-2.5 py-1 rounded ${activeTab === "investigation" ? "text-indigo-400 font-bold" : "text-slate-400"}`}
          >
            Live Room
          </button>
          <button
            onClick={() => setActiveTab("approvals")}
            className={`px-2.5 py-1 rounded ${activeTab === "approvals" ? "text-indigo-400 font-bold" : "text-slate-400"}`}
          >
            Approvals
          </button>
          <button
            onClick={() => setActiveTab("killswitch")}
            className={`px-2.5 py-1 rounded ${activeTab === "killswitch" ? "text-rose-400 font-bold" : "text-slate-400"}`}
          >
            Kill Switch
          </button>
        </div>
      </header>

      {/* Main Layout Grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 grid grid-cols-1 lg:grid-cols-4 gap-8 w-full">
        {/* Main Content Area (3 Cols) */}
        <main id="main-content" className="lg:col-span-3 space-y-6" tabIndex={-1}>
          {activeTab === "anomalies" && <AnomalyDashboardView />}
          {activeTab === "investigation" && <LiveInvestigationRoom />}
          {activeTab === "approvals" && <ApprovalCenterView />}
          {activeTab === "killswitch" && <KillSwitchPanel />}
        </main>

        {/* System Invariant Status Panel (1 Col) */}
        <aside className="space-y-6">
          <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-5 backdrop-blur shadow-lg">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-emerald-400" />
              System Invariant Status
            </h3>
            <ul className="space-y-3 text-xs">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-200 font-mono">INV-ACT-003:</strong>
                  <p className="text-slate-400">Zero Agent Self-Approval (Enforced)</p>
                </div>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-200 font-mono">DEC-009:</strong>
                  <p className="text-slate-400">SHA-256 Digest Binding (Verified)</p>
                </div>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-200 font-mono">INV-TEN-001:</strong>
                  <p className="text-slate-400">PostgreSQL RLS Boundary (Active)</p>
                </div>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-200 font-mono">INV-REL-001:</strong>
                  <p className="text-slate-400">Continuous WAL Durability (Pass)</p>
                </div>
              </li>
            </ul>
          </div>

          <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-5 backdrop-blur shadow-lg text-xs space-y-2">
            <h4 className="font-semibold text-slate-200">Platform Specifications</h4>
            <p className="text-slate-400">
              Build: <code className="text-indigo-300 font-mono">v1.0.0-rc1</code>
            </p>
            <p className="text-slate-400">
              Frontend Contract: <span className="text-slate-300 font-mono">FRONTEND-SPEC.md</span>
            </p>
            <p className="text-slate-400">
              Target Conformance: <span className="text-emerald-400 font-medium">WCAG 2.2 AA</span>
            </p>
          </div>
        </aside>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-900/60 py-4 text-center text-xs text-slate-500">
        RevPilot AI &mdash; Enterprise Autonomous Revenue Governance Platform &bull; Conforms to WCAG 2.2 AA &bull; Build <code>v1.0.0-rc1</code>
      </footer>
    </div>
  );
};
