import React, { useEffect, useState } from "react";
import { apiClient } from "../../api/client";
import { FinOpsBudgetSummary } from "../../api/types";
import {
  DollarSign,
  PieChart,
  Cpu,
  AlertCircle,
  ShieldCheck,
  TrendingUp,
  Clock,
  Lock,
  Layers,
  Sparkles,
} from "lucide-react";

export const FinOpsBudgetView: React.FC = () => {
  const [budget, setBudget] = useState<FinOpsBudgetSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadBudget() {
      setLoading(true);
      try {
        const res = await apiClient.getFinOpsBudget();
        setBudget(res);
      } catch (err) {
        console.error("Failed to load FinOps budget", err);
      } finally {
        setLoading(false);
      }
    }
    loadBudget();
  }, []);

  if (loading || !budget) {
    return (
      <div className="py-12 text-center text-slate-400 text-xs">
        Loading multi-dimensional token usage and budget ledger...
      </div>
    );
  }

  const quotaColor =
    budget.monthly_quota_pct > 80
      ? "bg-rose-500"
      : budget.monthly_quota_pct > 60
      ? "bg-amber-500"
      : "bg-emerald-500";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-5 backdrop-blur shadow-lg">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                <DollarSign className="w-3.5 h-3.5" />
                FINOPS GOVERNANCE LEDGER
              </span>
              <span className="text-xs font-mono text-slate-400">INV-COST-001 Hard Cap Enforcement</span>
            </div>
            <h2 className="text-xl font-bold text-slate-100 mt-2">
              Token Budget Allocation & Spend Reservation
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Hierarchical cost attribution: Tenant &rarr; Principal &rarr; Investigation &rarr; Tool. Atomic spend pre-authorization prevents over-allocation.
            </p>
          </div>

          <div className="text-right">
            <span className="text-xs text-slate-400 block font-mono">Monthly Reset Cycle</span>
            <span className="text-sm font-bold text-slate-200 font-mono">24 Days Remaining</span>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-400 text-xs font-medium block">Hard Spend Limit Cap</span>
          <span className="text-2xl font-bold text-slate-100 font-mono mt-1 block">
            ${budget.hard_spend_limit_usd.toFixed(2)}
          </span>
          <span className="text-[10px] text-slate-500 mt-1 block">Strict policy ceiling (HTTP 402 on breach)</span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-400 text-xs font-medium block">Committed Spend</span>
          <span className="text-2xl font-bold text-indigo-300 font-mono mt-1 block">
            ${budget.committed_spend_usd.toFixed(2)}
          </span>
          <span className="text-[10px] text-indigo-400/80 mt-1 block">Reconciled provider invocations</span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-400 text-xs font-medium block">In-Flight Reservations</span>
          <span className="text-2xl font-bold text-amber-300 font-mono mt-1 block">
            ${budget.reserved_spend_usd.toFixed(2)}
          </span>
          <span className="text-[10px] text-amber-400/80 mt-1 block">
            {budget.active_reservations_count} active multi-tenant locks
          </span>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4">
          <span className="text-slate-400 text-xs font-medium block">Remaining Discretionary</span>
          <span className="text-2xl font-bold text-emerald-400 font-mono mt-1 block">
            ${budget.remaining_spend_usd.toFixed(2)}
          </span>
          <span className="text-[10px] text-emerald-500/80 mt-1 block">Available for autonomous DAGs</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-slate-200 flex items-center gap-2">
            <PieChart className="w-4 h-4 text-indigo-400" />
            Monthly Quota Utilization
          </span>
          <span className="font-mono font-bold text-slate-100">{budget.monthly_quota_pct.toFixed(1)}% Consumed</span>
        </div>

        <div className="w-full bg-slate-950 rounded-full h-3 overflow-hidden border border-slate-800">
          <div
            className={`h-full rounded-full transition-all duration-500 ${quotaColor}`}
            style={{ width: `${budget.monthly_quota_pct}%` }}
          />
        </div>

        <div className="flex justify-between text-[11px] text-slate-400 font-mono pt-1">
          <span>$0.00</span>
          <span>$500.00 (Soft Warning Threshold)</span>
          <span>${budget.hard_spend_limit_usd.toFixed(2)} (Hard Cap)</span>
        </div>
      </div>

      {/* Token Usage & Dimension Attribution Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Token Attribution */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-400" />
            Multi-Dimensional Token Breakdown
          </h3>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <div>
                <span className="text-slate-200 font-medium block">Prompt Context Tokens</span>
                <span className="text-[11px] text-slate-500 font-mono">System prompts, citations & tool schemas</span>
              </div>
              <span className="text-indigo-300 font-mono font-bold text-sm">
                {budget.tokens_prompt.toLocaleString()}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <div>
                <span className="text-slate-200 font-medium block">Completion / Reasoning Tokens</span>
                <span className="text-[11px] text-slate-500 font-mono">Structured JSON hypotheses & action plans</span>
              </div>
              <span className="text-emerald-400 font-mono font-bold text-sm">
                {budget.tokens_completion.toLocaleString()}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
              <div>
                <span className="text-slate-200 font-medium block">Total Incurred LLM Cost</span>
                <span className="text-[11px] text-slate-500 font-mono">Blended rate $0.003/1k prompt, $0.015/1k completion</span>
              </div>
              <span className="text-slate-100 font-mono font-bold text-sm">
                ${budget.estimated_cost_usd.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Active Reservations & Concurrency Locks */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Lock className="w-4 h-4 text-amber-400" />
            Active Spend Reservation Tokens (INV-COST-001)
          </h3>

          <div className="space-y-3 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="flex justify-between items-center text-[11px]">
                <span className="text-indigo-400 font-semibold">tok_res_01h8x_arr_decay</span>
                <span className="text-emerald-400">$18.00 Reserved</span>
              </div>
              <p className="text-[10px] text-slate-400 font-sans">
                Investigation DAG: net_mrr_expansion_anomaly &bull; TTL: 14m 20s remaining
              </p>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="flex justify-between items-center text-[11px]">
                <span className="text-indigo-400 font-semibold">tok_res_01h8x_carrier_study</span>
                <span className="text-emerald-400">$22.00 Reserved</span>
              </div>
              <p className="text-[10px] text-slate-400 font-sans">
                Causal Study: doubly_robust_aipw_simulation &bull; TTL: 08m 45s remaining
              </p>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-1">
              <div className="flex justify-between items-center text-[11px]">
                <span className="text-indigo-400 font-semibold">tok_res_01h8x_action_intent</span>
                <span className="text-emerald-400">$8.00 Reserved</span>
              </div>
              <p className="text-[10px] text-slate-400 font-sans">
                Action Preflight: issue_credit_voucher &bull; TTL: 28m 10s remaining
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
