/**
 * RevPilot AI — Anomaly & Evidence Explorer Component
 * Conforms to:
 * - docs/28-frontend/FRONTEND-SPEC.md
 * - docs/07-data-platform/METRIC-SERVICE-SPEC.md
 * - Invariant: No Chain-of-Thought exposure to UI
 */

export interface MockAnomalyItem {
  id: string;
  metric: string;
  deviation: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  detected_at: string;
  citations: Array<{
    id: string;
    source: string;
    date: string;
    classification: string;
    summary: string;
    provenance_hash: string;
  }>;
}

export const MOCK_ANOMALIES: MockAnomalyItem[] = [
  {
    id: "anom_01h8x8a7b3c1",
    metric: "Net MRR Expansion Rate",
    deviation: "-24.6% vs baseline",
    severity: "HIGH",
    detected_at: "2026-09-04 22:15 UTC",
    citations: [
      {
        id: "cite_str_01",
        source: "Stripe Billing Webhook Events Stream",
        date: "2026-09-04",
        classification: "RESTRICTED",
        summary: "3 Tier-1 enterprise customers downgrading seats post SLA dispute.",
        provenance_hash: "sha256:4a3b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b",
      },
      {
        id: "cite_crm_02",
        source: "Salesforce CRM Opportunity Closed-Lost Ledger",
        date: "2026-09-03",
        classification: "CONFIDENTIAL",
        summary: "Renewal negotiation paused pending executive approval voucher.",
        provenance_hash: "sha256:9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e",
      },
    ],
  },
];

export class AnomalyDashboardComponent {
  private container: HTMLElement;

  constructor(containerId: string) {
    const el = document.getElementById(containerId);
    if (!el) throw new Error(`Element #${containerId} not found`);
    this.container = el;
  }

  public render(items: MockAnomalyItem[] = MOCK_ANOMALIES): void {
    this.container.innerHTML = items
      .map(
        (item) => `
        <article class="approval-card" aria-labelledby="anom-title-${item.id}">
          <div class="card-header">
            <div>
              <span class="badge badge-tier3">${item.severity}</span>
              <strong id="anom-title-${item.id}" style="margin-left: 0.5rem;">${item.metric}</strong>
            </div>
            <span style="color: var(--status-red); font-weight: bold;">${item.deviation}</span>
          </div>

          <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 1rem;">
            Detected: ${item.detected_at} &bull; Tenant: <code>tenant_enterprise_01</code>
          </p>

          <div class="citations-section">
            <h4 style="font-size: 0.95rem; margin-bottom: 0.5rem;">Audited Evidence Citations (FRONTEND-SPEC §11):</h4>
            ${item.citations
              .map(
                (cite) => `
                <div class="digest-box" style="margin-bottom: 0.5rem;">
                  <div><strong>[${cite.classification}] ${cite.source}</strong> (Effective: ${cite.date})</div>
                  <div style="margin: 0.25rem 0;">${cite.summary}</div>
                  <div style="color: var(--text-muted); font-size: 0.75rem;">Provenance Hash: <code>${cite.provenance_hash}</code></div>
                </div>
              `
              )
              .join("")}
          </div>

          <div style="margin-top: 0.75rem; font-size: 0.8rem; color: var(--text-muted);">
            ℹ️ <em>Citations derive from immutable facts. Hidden reasoning (chain-of-thought) is strictly excluded per privacy governance.</em>
          </div>
        </article>
      `
      )
      .join("");
  }
}
