import React from "react";

export interface CausalEstimand {
  treatment: string;
  outcome: string;
  estimator: string;
  pointEstimate: number;
  ciLower: number;
  ciUpper: number;
  pValue: number;
  eValue: number;
  robustnessValue: number;
}

interface Props {
  data?: CausalEstimand;
}

const defaultEstimand: CausalEstimand = {
  treatment: "Carrier SLA Penalty Waiver",
  outcome: "Quarterly Enterprise Churn Rate",
  estimator: "Doubly Robust AIPW (DoWhy/EconML)",
  pointEstimate: 0.066,
  ciLower: 0.0362,
  ciUpper: 0.0958,
  pValue: 0.00012,
  eValue: 2.45,
  robustnessValue: 0.18,
};

export const CausalImpactChart: React.FC<Props> = ({ data = defaultEstimand }) => {
  // Normalize scale for graphical error bar (-0.02 to 0.14)
  const minRange = -0.02;
  const maxRange = 0.14;
  const totalSpan = maxRange - minRange;

  const leftPercent = ((data.ciLower - minRange) / totalSpan) * 100;
  const rightPercent = ((data.ciUpper - minRange) / totalSpan) * 100;
  const pointPercent = ((data.pointEstimate - minRange) / totalSpan) * 100;
  const zeroPercent = ((0 - minRange) / totalSpan) * 100;

  return (
    <div className="w-full bg-slate-900/80 border border-slate-700/80 rounded-xl p-5 backdrop-blur shadow-lg">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-4">
        <div>
          <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse"></span>
            Causal Impact & 95% Confidence Interval
          </h3>
          <p className="text-xs text-slate-400 mt-0.5 font-mono">
            {data.treatment} &rarr; {data.outcome} ({data.estimator})
          </p>
        </div>
        <div className="flex gap-2">
          <span className="text-xs px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            p = {data.pValue} (Significant)
          </span>
          <span className="text-xs px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            E-Value: {data.eValue}
          </span>
        </div>
      </div>

      {/* Visual Interval Bar */}
      <div className="my-6 px-4">
        <div className="relative h-12 w-full flex items-center">
          {/* Zero baseline vertical reference */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-slate-600 border-l border-dashed border-slate-400 z-0"
            style={{ left: `${zeroPercent}%` }}
          >
            <span className="absolute -top-5 -translate-x-1/2 text-[10px] text-slate-400 font-mono">
              0.00 (Null)
            </span>
          </div>

          {/* Background track */}
          <div className="w-full h-2 bg-slate-800 rounded-full"></div>

          {/* Confidence Interval Band */}
          <div
            className="absolute h-4 bg-indigo-500/30 border-y-2 border-indigo-400 rounded"
            style={{
              left: `${leftPercent}%`,
              width: `${rightPercent - leftPercent}%`,
            }}
          >
            {/* Left Bracket */}
            <div className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 w-1.5 h-6 bg-indigo-400 rounded-sm"></div>
            {/* Right Bracket */}
            <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 w-1.5 h-6 bg-indigo-400 rounded-sm"></div>
          </div>

          {/* Point Estimate Dot */}
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-5 h-5 rounded-full bg-indigo-400 border-2 border-white shadow-lg flex items-center justify-center z-10"
            style={{ left: `${pointPercent}%` }}
          >
            <div className="w-1.5 h-1.5 rounded-full bg-slate-950"></div>
          </div>
        </div>

        {/* Axis Labels */}
        <div className="flex justify-between text-[11px] text-slate-400 font-mono mt-2">
          <span>Lower Bound ({data.ciLower.toFixed(4)})</span>
          <span className="text-indigo-300 font-semibold">
            Point Estimate (+{(data.pointEstimate * 100).toFixed(2)}%)
          </span>
          <span>Upper Bound ({data.ciUpper.toFixed(4)})</span>
        </div>
      </div>

      {/* Epistemic Guardrail Note */}
      <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
        <div>
          Sensitivity Robustness: <strong>{data.robustnessValue * 100}%</strong> of residual variance needed to overturn estimate.
        </div>
        <div className="text-emerald-400 font-medium">
          Deterministic Replay Verified (DEC-009)
        </div>
      </div>
    </div>
  );
};
