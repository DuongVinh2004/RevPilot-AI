import React from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceDot,
} from "recharts";

export interface AnomalyPoint {
  timestamp: string;
  actual: number;
  expected: number;
  bandUpper: number;
  bandLower: number;
  isAnomaly?: boolean;
  score?: number;
}

interface Props {
  data?: AnomalyPoint[];
  metricName?: string;
}

const defaultData: AnomalyPoint[] = [
  { timestamp: "08:00", actual: 102.5, expected: 100.0, bandLower: 92.0, bandUpper: 108.0 },
  { timestamp: "10:00", actual: 98.4, expected: 99.5, bandLower: 91.5, bandUpper: 107.5 },
  { timestamp: "12:00", actual: 105.1, expected: 101.0, bandLower: 93.0, bandUpper: 109.0 },
  { timestamp: "14:00", actual: 99.2, expected: 100.5, bandLower: 92.5, bandUpper: 108.5 },
  { timestamp: "16:00", actual: 75.4, expected: 100.0, bandLower: 92.0, bandUpper: 108.0, isAnomaly: true, score: 0.782 },
  { timestamp: "18:00", actual: 72.1, expected: 98.5, bandLower: 90.5, bandUpper: 106.5, isAnomaly: true, score: 0.815 },
  { timestamp: "20:00", actual: 80.0, expected: 97.0, bandLower: 89.0, bandUpper: 105.0, isAnomaly: true, score: 0.690 },
];

export const AnomalyTimeSeriesChart: React.FC<Props> = ({
  data = defaultData,
  metricName = "Net MRR Expansion Rate (%)",
}) => {
  const anomalyPoints = data.filter((d) => d.isAnomaly);

  return (
    <div className="w-full bg-slate-900/80 border border-slate-700/80 rounded-xl p-5 backdrop-blur shadow-lg">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-4">
        <div>
          <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse"></span>
            {metricName} — Time-Series Baseline & Incident Anomaly
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Shaded band represents statistical baseline boundary (±2σ expected interval).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 font-mono">
            {anomalyPoints.length} Anomalies Detected
          </span>
        </div>
      </div>

      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 20, bottom: 0, left: -10 }}>
            <defs>
              <linearGradient id="bandFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.6} />
            <XAxis dataKey="timestamp" stroke="#94a3b8" tick={{ fontSize: 12 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} domain={["auto", "auto"]} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                borderColor: "#334155",
                borderRadius: "0.5rem",
                color: "#f8fafc",
                fontSize: "0.8rem",
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: "0.8rem", paddingTop: "0.5rem" }}
              iconType="circle"
            />
            {/* Confidence Band Upper */}
            <Area
              type="monotone"
              dataKey="bandUpper"
              stroke="transparent"
              fill="url(#bandFill)"
              name="Expected Range (Upper/Lower)"
            />
            {/* Expected Baseline Line */}
            <Line
              type="monotone"
              dataKey="expected"
              stroke="#818cf8"
              strokeDasharray="4 4"
              strokeWidth={2}
              dot={false}
              name="Baseline Expected"
            />
            {/* Actual Observed Value */}
            <Line
              type="monotone"
              dataKey="actual"
              stroke="#f43f5e"
              strokeWidth={2.5}
              name="Actual Metric"
              activeDot={{ r: 6 }}
            />
            {/* Marker dots on anomalies */}
            {anomalyPoints.map((pt, idx) => (
              <ReferenceDot
                key={idx}
                x={pt.timestamp}
                y={pt.actual}
                r={6}
                fill="#ef4444"
                stroke="#fee2e2"
                strokeWidth={2}
              />
            ))}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
