/**
 * RevPilot AI — Evidence & Hypothesis Viewer Component
 * Renders tamper-evident evidence citations and ranked hypotheses.
 */

export class EvidenceViewerComponent {
  private container: HTMLElement;

  constructor(containerId: string) {
    const el = document.getElementById(containerId);
    if (!el) throw new Error(`Element #${containerId} not found`);
    this.container = el;
  }

  render(): void {
    this.container.innerHTML = `
      <div class="card" style="margin-bottom: 1.5rem;">
        <h2 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem;">Evidence & Provenance Vault</h2>
        <p style="color: var(--text-muted); font-size: 0.875rem;">
          Cryptographically sealed evidence bundles and ranked causal hypotheses.
        </p>
      </div>

      <div class="card" style="margin-bottom: 1rem;">
        <h3 style="font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem;">Primary Causal Hypothesis</h3>
        <p style="font-size: 0.875rem; line-height: 1.5;">
          Carrier SLA penalty increase in US-EAST distribution hubs triggered abnormal churn among Tier-1 enterprise subscribers.
        </p>
        <div style="margin-top: 0.75rem; font-size: 0.75rem; color: var(--text-muted);">
          <span>Ordinal Rank: <strong>#1</strong></span> • 
          <span>Confidence: <strong>88.4%</strong></span> • 
          <span>ATE: <strong>+0.066 (p=0.0001)</strong></span>
        </div>
      </div>
    `;
  }
}
