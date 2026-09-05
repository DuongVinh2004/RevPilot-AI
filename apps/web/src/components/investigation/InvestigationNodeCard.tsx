import React from "react";
import { CheckCircle2, Clock, AlertCircle, PlayCircle } from "lucide-react";

export interface DAGNode {
  node_id: string;
  label: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  progress_pct: number;
  message: string;
  duration_ms?: number;
}

interface Props {
  node: DAGNode;
  isCurrent?: boolean;
}

export const InvestigationNodeCard: React.FC<Props> = ({ node, isCurrent = false }) => {
  const getStatusBadge = () => {
    switch (node.status) {
      case "COMPLETED":
        return (
          <span className="flex items-center gap-1 text-emerald-400 font-medium text-xs">
            <CheckCircle2 className="w-3.5 h-3.5" /> Done ({node.duration_ms}ms)
          </span>
        );
      case "RUNNING":
        return (
          <span className="flex items-center gap-1 text-indigo-400 font-medium text-xs animate-pulse">
            <PlayCircle className="w-3.5 h-3.5" /> Executing Activity...
          </span>
        );
      case "FAILED":
        return (
          <span className="flex items-center gap-1 text-rose-400 font-medium text-xs">
            <AlertCircle className="w-3.5 h-3.5" /> Failed
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-slate-500 text-xs">
            <Clock className="w-3.5 h-3.5" /> Queued
          </span>
        );
    }
  };

  return (
    <div
      className={`p-4 rounded-xl border transition ${
        isCurrent
          ? "bg-indigo-950/30 border-indigo-500/50 shadow-md shadow-indigo-500/10"
          : node.status === "COMPLETED"
          ? "bg-slate-900/70 border-emerald-500/30"
          : "bg-slate-950/60 border-slate-800"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-indigo-300 font-semibold">
            {node.node_id}
          </span>
          <h4 className="text-sm font-semibold text-slate-100">{node.label}</h4>
        </div>
        {getStatusBadge()}
      </div>

      <p className="text-xs text-slate-300 mt-1">{node.message}</p>

      {/* Progress Bar */}
      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mt-3">
        <div
          className={`h-full transition-all duration-500 ${
            node.status === "COMPLETED"
              ? "bg-emerald-500"
              : node.status === "RUNNING"
              ? "bg-indigo-500 animate-pulse"
              : "bg-slate-700"
          }`}
          style={{ width: `${node.progress_pct}%` }}
        ></div>
      </div>
    </div>
  );
};
