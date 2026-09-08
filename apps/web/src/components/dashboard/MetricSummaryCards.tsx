import React from "react";
import { AlertTriangle, TrendingDown, ShieldAlert, DollarSign } from "lucide-react";

interface Props {
  totalAnomalies: number;
  criticalCount: number;
  avgScore: number;
  revenueAtRisk: string;
}

export const MetricSummaryCards: React.FC<Props> = ({
  totalAnomalies,
  criticalCount,
  avgScore,
  revenueAtRisk,
}) => {
  const cards = [
    {
      title: "Active Anomalies",
      value: totalAnomalies.toString(),
      subtext: "Across active tenant cohorts",
      icon: AlertTriangle,
      color: "text-amber-400",
      bg: "bg-amber-500/10",
      border: "border-amber-500/20",
    },
    {
      title: "Critical Severity",
      value: criticalCount.toString(),
      subtext: "Requires human-in-the-loop review",
      icon: ShieldAlert,
      color: "text-rose-400",
      bg: "bg-rose-500/10",
      border: "border-rose-500/20",
    },
    {
      title: "Avg Anomaly Score",
      value: avgScore.toFixed(3),
      subtext: "Calibrated STL + Isolation Forest",
      icon: TrendingDown,
      color: "text-indigo-400",
      bg: "bg-indigo-500/10",
      border: "border-indigo-500/20",
    },
    {
      title: "Revenue at Risk",
      value: revenueAtRisk,
      subtext: "Projected annual recurring impact",
      icon: DollarSign,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <div
            key={i}
            className={`p-4 rounded-xl border ${c.border} bg-slate-900/60 backdrop-blur flex items-center justify-between shadow-sm`}
          >
            <div>
              <p className="text-xs font-medium text-slate-400">{c.title}</p>
              <h4 className="text-2xl font-bold text-slate-100 mt-1">{c.value}</h4>
              <p className="text-[11px] text-slate-400 mt-0.5">{c.subtext}</p>
            </div>
            <div className={`p-3 rounded-lg ${c.bg}`}>
              <Icon className={`w-5 h-5 ${c.color}`} />
            </div>
          </div>
        );
      })}
    </div>
  );
};
