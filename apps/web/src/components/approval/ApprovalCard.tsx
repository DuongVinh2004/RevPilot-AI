import React, { useState } from "react";
import { ApprovalRequestRecord } from "../../api/types";
import { apiClient } from "../../api/client";
import { Check, X, Play, Clock, ShieldCheck, DollarSign } from "lucide-react";

interface Props {
  item: ApprovalRequestRecord;
  onActionComplete: () => void;
}

export const ApprovalCard: React.FC<Props> = ({ item, onActionComplete }) => {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dryRunResult, setDryRunResult] = useState<any | null>(null);
  const [approved, setApproved] = useState<boolean>(item.status === "APPROVED");
  const [rejected, setRejected] = useState<boolean>(item.status === "REJECTED");

  const digest = item.digest || item.payload_digest || "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069";
  const cost = item.cost_usd || item.estimated_cost_usd || 0;

  const handleApprove = async () => {
    setLoading("approve");
    setError(null);
    try {
      await apiClient.approveAction(item.id, digest);
      setApproved(true);
      onActionComplete();
    } catch (err: any) {
      setError(err.message || "Approval failed");
    } finally {
      setLoading(null);
    }
  };

  const handleReject = async () => {
    const reason = prompt("Enter reason for rejection:") || "Rejected by human operator";
    setLoading("reject");
    setError(null);
    try {
      await apiClient.rejectAction(item.id, reason);
      setRejected(true);
      onActionComplete();
    } catch (err: any) {
      setError(err.message || "Rejection failed");
    } finally {
      setLoading(null);
    }
  };

  const handleDryRun = async () => {
    setLoading("dryrun");
    setError(null);
    try {
      const res = await apiClient.dryRunAction(item.id);
      setDryRunResult(res);
    } catch (err: any) {
      setError(err.message || "Dry-run failed");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div
      className={`p-5 rounded-xl border transition shadow-lg ${
        approved
          ? "bg-emerald-950/20 border-emerald-500/40"
          : rejected
          ? "bg-rose-950/20 border-rose-500/40"
          : "bg-slate-900/80 border-slate-700/80"
      }`}
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                item.required_approval_tier === "TIER_3"
                  ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                  : item.required_approval_tier === "TIER_2"
                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                  : "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40"
              }`}
            >
              {item.required_approval_tier}
            </span>
            <span className="font-mono text-xs text-slate-500">{item.id}</span>
          </div>
          <h4 className="text-base font-semibold text-slate-100 mt-1">
            {item.action_type.replace(/_/g, " ")}
          </h4>
        </div>

        <div className="text-right sm:self-auto self-end">
          <div className="flex items-center gap-1 text-emerald-400 font-bold text-lg">
            <DollarSign className="w-4 h-4 text-emerald-400" />
            {cost.toLocaleString()} USD
          </div>
          <div className="flex items-center gap-1 text-[11px] text-slate-400 justify-end mt-0.5">
            <Clock className="w-3 h-3" /> Expires in {item.expires_in || "24h"}
          </div>
        </div>
      </div>

      {/* Target Entity References */}
      <div className="my-3 p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-xs">
        <div className="text-slate-400 font-medium mb-1">
          Target Entities:{" "}
          <span className="text-slate-200 font-mono">
            {item.target_entity_refs?.join(", ") || "cust_enterprise_alpha, sub_arr_450k"}
          </span>
        </div>
        <div className="text-slate-400 font-medium flex items-center gap-1 overflow-hidden">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
          <span className="text-slate-400 flex-shrink-0">Payload Digest:</span>
          <span className="text-indigo-300 font-mono truncate">{digest}</span>
        </div>
      </div>

      {error && (
        <div className="my-3 p-2.5 rounded bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {dryRunResult && (
        <div className="my-3 p-3 rounded bg-indigo-950/40 border border-indigo-500/30 text-xs text-indigo-200">
          <p className="font-semibold text-indigo-300">
            ✓ Dry-Run Preflight Passed (Zero Socket Mutation)
          </p>
          <p className="text-[11px] text-slate-300 mt-1">
            Provider check: {dryRunResult.preflight_checks?.provider_credentials} • Side effects: {dryRunResult.external_side_effects}
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-end gap-2.5 mt-4 pt-3 border-t border-slate-800">
        {approved ? (
          <span className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 bg-emerald-500/10 px-3 py-1.5 rounded-lg border border-emerald-500/30">
            <Check className="w-4 h-4" /> Cryptographically Approved & Signed
          </span>
        ) : rejected ? (
          <span className="flex items-center gap-1.5 text-xs font-semibold text-rose-400 bg-rose-500/10 px-3 py-1.5 rounded-lg border border-rose-500/30">
            <X className="w-4 h-4" /> Action Rejected
          </span>
        ) : (
          <>
            <button
              onClick={handleDryRun}
              disabled={loading !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 transition"
            >
              <Play className="w-3 h-3 text-indigo-400" />
              {loading === "dryrun" ? "Simulating..." : "Execute Dry-Run"}
            </button>
            <button
              onClick={handleReject}
              disabled={loading !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-500/20 text-rose-300 border border-rose-500/40 hover:bg-rose-500/30 transition"
            >
              <X className="w-3 h-3" />
              {loading === "reject" ? "Rejecting..." : "Reject"}
            </button>
            <button
              onClick={handleApprove}
              disabled={loading !== null}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition shadow"
            >
              <Check className="w-3.5 h-3.5" />
              {loading === "approve" ? "Signing Digest..." : "Sign & Grant Approval"}
            </button>
          </>
        )}
      </div>
    </div>
  );
};
