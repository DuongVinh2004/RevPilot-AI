import React, { useEffect, useState } from "react";
import { apiClient } from "../../api/client";
import { EvidenceRecord, HypothesisRecord, ClaimVerificationResponse } from "../../api/types";
import {
  FileText,
  ShieldCheck,
  Search,
  Hash,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Copy,
  Check,
  Layers,
  ArrowRight,
} from "lucide-react";

export const EvidenceVaultView: React.FC = () => {
  const [evidenceList, setEvidenceList] = useState<EvidenceRecord[]>([]);
  const [hypotheses, setHypotheses] = useState<HypothesisRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // Claim Verifier Sandbox State
  const [claimStatement, setClaimStatement] = useState<string>(
    "Carrier SLA penalty breach increased enterprise churn by +6.6%"
  );
  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<string[]>([]);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verificationResult, setVerificationResult] = useState<ClaimVerificationResponse | null>(null);

  useEffect(() => {
    async function loadVault() {
      setLoading(true);
      try {
        const [evdRes, hypRes] = await Promise.all([
          apiClient.getInvestigationEvidence("inv_01h8abcde12345"),
          apiClient.getInvestigationHypotheses("inv_01h8abcde12345"),
        ]);
        setEvidenceList(evdRes.items);
        setHypotheses(hypRes.items);
        if (evdRes.items.length > 0) {
          setSelectedEvidenceIds([evdRes.items[0].id]);
        }
      } catch (err) {
        console.error("Failed to load evidence vault data", err);
      } finally {
        setLoading(false);
      }
    }
    loadVault();
  }, []);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedHash(text);
    setTimeout(() => setCopiedHash(null), 2000);
  };

  const handleToggleEvidence = (id: string) => {
    setSelectedEvidenceIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleVerifyClaim = async () => {
    if (!claimStatement.trim()) return;
    setVerifying(true);
    try {
      const res = await apiClient.verifyClaim(claimStatement, selectedEvidenceIds);
      setVerificationResult(res);
    } catch (err: any) {
      setVerificationResult({
        claim_id: "clm_error",
        statement: claimStatement,
        verifier_status: "UNSUPPORTED",
        rejection_reason: err.message || "Failed to verify claim",
        evidence_cited_count: selectedEvidenceIds.length,
        verified_at: new Date().toISOString(),
      });
    } finally {
      setVerifying(false);
    }
  };

  const filteredEvidence = evidenceList.filter((e) => {
    if (selectedFilter === "ALL") return true;
    return e.classification === selectedFilter;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900/80 border border-slate-700/80 rounded-xl p-5 backdrop-blur shadow-lg">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                IMMUTABLE PROVENANCE VAULT
              </span>
              <span className="text-xs font-mono text-slate-400">pgvector HNSW (1536 dim, cosine &lt;=&gt;)</span>
            </div>
            <h2 className="text-xl font-bold text-slate-100 mt-2">
              Evidence Ledger & Formal Claim Verifier
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Every inference and causal claim requires tamper-evident provenance citations. Anti-hallucination Invariant (INV-EVD-001) enforced.
            </p>
          </div>

          {/* Classification Filters */}
          <div className="flex items-center gap-1.5 bg-slate-950/80 border border-slate-800 p-1 rounded-lg text-xs">
            {["ALL", "RESTRICTED", "INTERNAL"].map((f) => (
              <button
                key={f}
                onClick={() => setSelectedFilter(f)}
                className={`px-3 py-1 rounded font-medium transition ${
                  selectedFilter === f
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Grid: Vector Evidence Chunks (Left 2 cols) & Ranked Hypotheses (Right 1 col) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            Verified Vector Document Chunks ({filteredEvidence.length})
          </h3>

          {loading ? (
            <div className="p-8 text-center text-slate-400 text-xs bg-slate-900/60 rounded-xl border border-slate-800">
              Loading vector chunks from pgvector evidence store...
            </div>
          ) : (
            filteredEvidence.map((chunk) => {
              const isSelected = selectedEvidenceIds.includes(chunk.id);
              return (
                <div
                  key={chunk.id}
                  className={`bg-slate-900/80 border rounded-xl p-4 transition ${
                    isSelected ? "border-indigo-500/80 bg-slate-900/95" : "border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleToggleEvidence(chunk.id)}
                        className="w-4 h-4 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-slate-900"
                      />
                      <span className="font-mono text-xs font-bold text-slate-200">
                        {chunk.document_id}
                      </span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                        chunk #{chunk.chunk_index}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          chunk.classification === "RESTRICTED"
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                            : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        }`}
                      >
                        {chunk.classification}
                      </span>
                    </div>

                    {chunk.similarity_score && (
                      <span className="text-[11px] font-mono text-emerald-400 font-semibold bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/30">
                        cosine {(chunk.similarity_score * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-slate-300 mt-2.5 font-serif leading-relaxed bg-slate-950/50 p-3 rounded-lg border border-slate-800/80">
                    "{chunk.content}"
                  </p>

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/80 text-[11px] text-slate-400">
                    <div className="flex items-center gap-1.5 font-mono">
                      <Hash className="w-3.5 h-3.5 text-slate-500" />
                      <span className="truncate max-w-[260px]">{chunk.content_digest}</span>
                      <button
                        onClick={() => handleCopy(chunk.content_digest)}
                        className="p-1 hover:text-slate-200 text-slate-500 transition"
                        title="Copy SHA-256 digest"
                      >
                        {copiedHash === chunk.content_digest ? (
                          <Check className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </button>
                    </div>

                    <span className="font-mono text-slate-500">
                      Effective: {new Date(chunk.effective_from).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Col: Ranked Hypotheses */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            Ranked Causal Hypotheses ({hypotheses.length})
          </h3>

          <div className="space-y-3">
            {hypotheses.map((h, idx) => (
              <div
                key={h.hypothesis_id}
                className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    Rank #{idx + 1} &bull; {h.ranking_method}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      h.status === "SUPPORTED"
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                        : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                    }`}
                  >
                    {h.status}
                  </span>
                </div>

                <p className="text-xs text-slate-200 leading-relaxed font-medium">
                  {h.statement}
                </p>

                <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800 text-[11px] font-mono">
                  <div>
                    <span className="text-slate-500 block text-[10px]">ATE Effect</span>
                    <strong className="text-indigo-300">+{h.ate_point_estimate.toFixed(3)}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">P-Value</span>
                    <strong className="text-emerald-400">{h.p_value.toFixed(4)}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">E-Value</span>
                    <strong className="text-amber-300">{h.e_value.toFixed(2)}</strong>
                  </div>
                </div>

                <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
                  <span>Evidence Coverage</span>
                  <span className="font-mono text-slate-200 font-semibold">
                    {(h.evidence_coverage_ratio * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Claim Verifier Interactive Sandbox */}
      <div className="bg-slate-900/90 border-2 border-indigo-500/40 rounded-xl p-5 shadow-xl">
        <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-indigo-400" />
          Interactive Claim Verifier Sandbox (Rules 1&ndash;10 Engine)
        </h3>
        <p className="text-xs text-slate-400 mt-1">
          Simulate autonomous verification. Tests for ungrounded assertions, temporal lookahead leakage, correlation-as-causation fallacies, and self-authorization bypass.
        </p>

        <div className="mt-4 space-y-3">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Enter Revenue Finding / Claim Statement:
            </label>
            <input
              type="text"
              value={claimStatement}
              onChange={(e) => setClaimStatement(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-indigo-500 font-medium"
              placeholder="e.g. Carrier SLA delay caused customer churn..."
            />
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-1">
            <span className="text-xs text-slate-400">
              Cited Evidence References:{" "}
              <strong className="text-indigo-300 font-mono">
                {selectedEvidenceIds.length > 0 ? selectedEvidenceIds.join(", ") : "None selected (Will fail Rule 1)"}
              </strong>
            </span>

            <button
              onClick={handleVerifyClaim}
              disabled={verifying}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg transition"
            >
              {verifying ? "Verifying Invariant AST..." : "Verify Claim Against Rules"}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Verification Verdict Box */}
          {verificationResult && (
            <div
              className={`mt-4 p-4 rounded-xl border text-xs space-y-1.5 ${
                verificationResult.verifier_status === "VERIFIED"
                  ? "bg-emerald-950/40 border-emerald-500/50 text-emerald-200"
                  : verificationResult.verifier_status === "CONTRADICTED"
                  ? "bg-rose-950/40 border-rose-500/50 text-rose-200"
                  : "bg-amber-950/40 border-amber-500/50 text-amber-200"
              }`}
            >
              <div className="flex items-center gap-2 font-bold text-sm">
                {verificationResult.verifier_status === "VERIFIED" ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : verificationResult.verifier_status === "CONTRADICTED" ? (
                  <XCircle className="w-4 h-4 text-rose-400" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                )}
                VERDICT: {verificationResult.verifier_status}
              </div>

              {verificationResult.rejection_reason && (
                <p className="font-mono text-[11px] text-rose-300/90">
                  {verificationResult.rejection_reason}
                </p>
              )}

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400">
                <span>Citations Cited: {verificationResult.evidence_cited_count}</span>
                <span>Verified At: {new Date(verificationResult.verified_at).toLocaleTimeString()}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
