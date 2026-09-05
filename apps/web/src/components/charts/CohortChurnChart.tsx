import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";

export interface CohortItem {
  segment: string;
  baselineChurnPct: number;
  postInterventionChurnPct: number;
  retainedArrUsd: number;
}

interface Props {
  data?: CohortItem[];
}

const defaultCohorts: CohortItem[] = [
  { segment: "Enterprise Tier-1", baselineChurnPct: 18.2, postInterventionChurnPct: 8.4, retainedArrUsd: 142000 },
  { segment: "Mid-Market Growth", baselineChurnPct: 24.5, postInterventionChurnPct: 14.1, retainedArrUsd: 85000 },
  { segment: "SMB High-Volume", baselineChurnPct: 31.0, postInterventionChurnPct: 22.0, retainedArrUsd: 46000 },
  { segment: "Self-Serve Core", baselineChurnPct: 38.4, postInterventionChurnPct: 30.5, retainedArrUsd: 21000 },
];

export const CohortChurnChart: React.FC<Props> = ({ data = defaultCohorts }) => {
  return (
    <div className="w-full bg-slate-900/80 border border-slate-700/80 rounded-xl p-5 backdrop-blur shadow-lg">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-4">
        <div>
          <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            Customer Cohort Churn Hazard vs. Uplift Potential
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Compares baseline churn hazard with causal counterfactual after targeted credit voucher intervention.
          </p>
        </div>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 20, bottom: 0, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.6} />
            <XAxis dataKey="segment" stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <YAxis
              stroke="#94a3b8"
              tick={{ fontSize: 11 }}
              unit="%"
              domain={[0, 50]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                borderColor: "#334155",
                borderRadius: "0.5rem",
                color: "#f8fafc",
                fontSize: "0.8rem",
              }}
              formatter={(val: any, name: string) => [
                `${val}%`,
                name === "baselineChurnPct" ? "Baseline Churn Risk" : "Post-Intervention Churn",
              ]}
            />
            <Legend wrapperStyle={{ fontSize: "0.8rem" }} />
            <Bar
              dataKey="baselineChurnPct"
              name="Baseline Churn Risk (%)"
              fill="#ef4444"
              radius={[4, 4, 0, 0]}
            />
            <Bar
              dataKey="postInterventionChurnPct"
              name="Post-Intervention Churn (%)"
              fill="#10b981"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
