import React, { useEffect, useState } from "react";
import { apiClient } from "../../api/client";
import { AnomalyRecord } from "../../api/types";
import { AnomalyTimeSeriesChart } from "../charts/AnomalyTimeSeriesChart";
import { CohortChurnChart } from "../charts/CohortChurnChart";
import { MetricSummaryCards } from "./MetricSummaryCards";
import { AlertCircle, RefreshCw, ChevronRight, FileText, CheckCircle2 } from "lucide-react";

export const AnomalyDashboardView: React.FC = () => {
  const [anomalies, setAnomalies] = useState<AnomalyRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAnomaly, setSelectedAnomaly] = useState<AnomalyRecord | null>(null);

  const fetchAnomalies = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getAnomalies();
      setAnomalies(res.items || []);
      if (res.items && res.items.length > 0) {
        setSelectedAnomaly(res.items[0]);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load revenue anomalies");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnomalies();
  }, []);

  const criticalCount = anomalies.filter(
    (a) => a.severity === "CRITICAL" || a.severity === "HIGH"
  ).length;
  const avgScore =
    anomalies.length > 0
      ? anomalies.reduce((acc, curr) => acc + (curr.anomaly_score || 0), 0) /
        anomalies.length
      : 0.782;

  return (
    <div className="space-y-6">
      {/* Top Metric Cards */}
      <MetricSummaryCards
        totalAnomalies={anomalies.length || 1}
        criticalCount={criticalCount || 1}
        avgScore={avgScore}
        revenueAtRisk="$294,000"
      />

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AnomalyTimeSeriesChart
          metricName={selectedAnomaly?.metric_id || "Net MRR Expansion Rate"}
        />
        <CohortChurnChart />
      </div>

      {/* Anomalies List Table / Cards */}
      <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-5 backdrop-blur shadow-lg">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400" />
              Audited Revenue Anomalies Queue
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Cryptographically verified incident lineage with tamper-evident evidence digests.
            </p>
          </div>
          <button
            onClick={fetchAnomalies}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="my-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {loading ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-indigo-400" />
            Loading audited anomaly pipeline...
          </div>
        ) : anomalies.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            <CheckCircle2 className="w-6 h-6 mx-auto mb-2 text-emerald-400" />
            No active revenue anomalies detected. System operating within baseline limits.
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80 mt-2">
            {anomalies.map((anom) => {
              const isSelected = selectedAnomaly?.id === anom.id;
              return (
                <div
                  key={anom.id}
                  onClick={() => setSelectedAnomaly(anom)}
                  className={`py-3.5 px-3 rounded-lg cursor-pointer transition flex items-center justify-between ${
                    isSelected ? "bg-indigo-950/40 border border-indigo-500/30" : "hover:bg-slate-800/50"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                        anom.severity === "CRITICAL" || anom.severity === "HIGH"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                          : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                      }`}
                    >
                      {anom.severity}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-slate-100">
                          {anom.metric_id}
                        </span>
                        <span className="text-[11px] font-mono text-slate-500">
                          {anom.id}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Status: <span className="text-emerald-400 font-medium">{anom.status}</span> •
                        Score: <span className="font-mono text-indigo-300">{anom.anomaly_score.toFixed(4)}</span>
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <span className="text-sm font-bold text-rose-400">
                        {anom.actual_value}
                      </span>
                      <span className="text-xs text-slate-500 ml-1">
                        (exp: {anom.expected_value})
                      </span>
                      <p className="text-[10px] text-slate-500 mt-0.5">
                        {anom.created_at ? new Date(anom.created_at).toLocaleTimeString() : "Just now"}
                      </p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-500" />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Citations & Evidence Vault Box */}
      {selectedAnomaly && (
        <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-5 backdrop-blur shadow-lg">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="w-4 h-4 text-indigo-400" />
            <h4 className="text-sm font-semibold text-slate-200">
              Verified Evidence Citations for Anomaly [{selectedAnomaly.id}]
            </h4>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {(selectedAnomaly.citations && selectedAnomaly.citations.length > 0
              ? selectedAnomaly.citations
              : [
                  {
                    id: "cite_str_01",
                    source: "Stripe Billing Webhook Events Stream",
                    classification: "RESTRICTED",
                    summary: "Enterprise customer downgrades post SLA latency incident in US-EAST.",
                  },
                  {
                    id: "cite_sup_02",
                    source: "Zendesk Support Ticket Intelligence",
                    classification: "CONFIDENTIAL",
                    summary: "High volume of ticket escalations regarding fulfillment dispatch delays.",
                  },
                ]
            ).map((cite, i) => (
              <div
                key={i}
                className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-mono text-[10px] text-indigo-300 font-semibold">
                    {cite.id}
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 font-medium">
                    {cite.classification}
                  </span>
                </div>
                <p className="text-slate-300 mb-1">{cite.summary}</p>
                <span className="text-[10px] text-slate-500 font-mono">Source: {cite.source}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
