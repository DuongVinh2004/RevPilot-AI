import React, { useState } from "react";
import { apiClient } from "../../api/client";
import { AlertOctagon, ShieldAlert, CheckCircle2, Lock } from "lucide-react";

export const KillSwitchPanel: React.FC = () => {
  const [reason, setReason] = useState<string>("");
  const [scope, setScope] = useState<string>("GLOBAL");
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleEngage = async () => {
    if (!reason.trim()) {
      setError("Mandatory activation reason required for tamper-evident audit ledger (INV-AUD-001).");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.engageKillSwitch(scope, reason);
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Kill switch engagement failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-rose-950/30 border-2 border-rose-600/80 rounded-xl p-6 backdrop-blur shadow-xl">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-3 rounded-xl bg-rose-600/20 border border-rose-500/40 text-rose-400">
            <AlertOctagon className="w-7 h-7" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-rose-200">
              Emergency Action Kill Switch (Circuit Breaker)
            </h2>
            <p className="text-xs text-rose-300/80 mt-0.5">
              Instantly halts physical external mutation dispatches across tenants and capability adapters.
              Propagation SLA &lt; 500ms (Fail-Closed INV-ACT-001).
            </p>
          </div>
        </div>

        {/* Input Scope & Reason */}
        <div className="my-5 space-y-4 max-w-xl">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Select Enforcement Scope:
            </label>
            <div className="flex gap-3">
              {["GLOBAL", "TENANT", "CAPABILITY"].map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setScope(s)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                    scope === s
                      ? "bg-rose-600 text-white border-rose-400"
                      : "bg-slate-900/80 text-slate-300 border-slate-700 hover:bg-slate-800"
                  }`}
                >
                  {s} Scope
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="killswitch-input" className="block text-xs font-semibold text-slate-300 mb-1">
              Mandatory Audit Reason (Ledger INV-AUD-001):
            </label>
            <input
              id="killswitch-input"
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Upstream carrier API returning corrupted payload data"
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-rose-500"
            />
          </div>
        </div>

        {error && (
          <div className="my-3 p-3 rounded-lg bg-rose-500/20 border border-rose-500/50 text-rose-200 text-xs flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {result && (
          <div className="my-4 p-4 rounded-xl bg-rose-900/40 border-2 border-rose-500 text-xs text-rose-100 space-y-1">
            <div className="flex items-center gap-2 font-bold text-sm text-rose-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              🛑 CIRCUIT BREAKER ACTIVELY ENGAGED
            </div>
            <p className="font-mono">Kill Switch ID: {result.kill_switch_id}</p>
            <p>
              Propagation Latency: <strong>{result.propagation_latency_ms}ms</strong> (SLA &lt; 500ms Met)
            </p>
            <p className="text-rose-300/80">Reason: {result.reason}</p>
          </div>
        )}

        <button
          onClick={handleEngage}
          disabled={loading}
          className="mt-2 flex items-center gap-2 px-5 py-3 rounded-lg text-sm font-bold bg-rose-600 hover:bg-rose-500 text-white border border-rose-400 shadow-lg shadow-rose-900/50 transition cursor-pointer"
        >
          <Lock className="w-4 h-4" />
          {loading ? "Engaging Circuit Breaker..." : `🛑 ENGAGE ${scope} KILL SWITCH`}
        </button>
      </div>
    </div>
  );
};
