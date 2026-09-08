import React, { useEffect, useState } from "react";
import { apiClient } from "../../api/client";
import { ApprovalRequestRecord } from "../../api/types";
import { ApprovalCard } from "./ApprovalCard";
import { ShieldCheck, RefreshCw, AlertTriangle } from "lucide-react";

export const ApprovalCenterView: React.FC = () => {
  const [approvals, setApprovals] = useState<ApprovalRequestRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchApprovals = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getApprovals();
      setApprovals(res.items || []);
    } catch (err: any) {
      setError(err.message || "Failed to load approvals queue");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-5 backdrop-blur shadow-lg">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              Governed Human Approval Center
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Mutations exceeding policy authority tiers require cryptographically verified human operator signatures.
              AI agent self-approval is strictly forbidden (<strong>INV-ACT-003</strong>).
            </p>
          </div>
          <button
            onClick={fetchApprovals}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh Queue
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Approvals List */}
      {loading ? (
        <div className="py-12 text-center text-slate-400 text-xs">
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-indigo-400" />
          Loading pending authorization queue...
        </div>
      ) : approvals.length === 0 ? (
        <div className="p-8 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-slate-400 text-sm">
          No pending approvals in queue. All dispatched interventions have completed or passed preflight.
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((item) => (
            <ApprovalCard key={item.id} item={item} onActionComplete={fetchApprovals} />
          ))}
        </div>
      )}
    </div>
  );
};
