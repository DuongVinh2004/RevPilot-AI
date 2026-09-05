/**
 * RevPilot AI — Anomaly & Evidence Explorer Component
 * Conforms to:
 * - docs/28-frontend/FRONTEND-SPEC.md
 * - docs/07-data-platform/METRIC-SERVICE-SPEC.md
 * - Invariant: No Chain-of-Thought exposure to UI
 */

import { apiClient } from '../api/client';
import { AnomalyRecord } from '../api/types';

export class AnomalyDashboardComponent {
  private container: HTMLElement;

  constructor(containerId: string) {
    const el = document.getElementById(containerId);
    if (!el) throw new Error(`Element #${containerId} not found`);
    this.container = el;
  }

  async render(): Promise<void> {
    this.container.innerHTML = `
      <div class="card" style="margin-bottom: 1.5rem;">
        <h2 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem;">Active Revenue Anomalies</h2>
        <p style="color: var(--text-muted); font-size: 0.875rem;">
          Detected deviations requiring human-in-the-loop investigation. Evidence spans verified against cryptographic ledger hashes.
        </p>
      </div>
      <div id="anomalies-list-container">
        <p style="color: var(--text-muted); font-size: 0.875rem;">Loading anomalies from server...</p>
      </div>
    `;

    try {
      const response = await apiClient.getAnomalies();
      const listContainer = document.getElementById('anomalies-list-container');
      if (!listContainer) return;

      if (!response.items || response.items.length === 0) {
        listContainer.innerHTML = '<p style="color: var(--text-muted);">No active anomalies detected.</p>';
        return;
      }

      listContainer.innerHTML = response.items.map((anom: AnomalyRecord) => `
        <div class="card" style="margin-bottom: 1.5rem; border-left: 4px solid var(--accent-red);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
            <div>
              <span class="badge badge-critical">${anom.severity}</span>
              <span style="font-family: monospace; font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem;">${anom.id}</span>
              <h3 style="font-size: 1.125rem; font-weight: 600; margin-top: 0.25rem;">${anom.metric_id}</h3>
            </div>
            <div style="text-align: right;">
              <span style="font-size: 1.125rem; font-weight: 700; color: var(--accent-red);">${anom.actual_value} (expected: ${anom.expected_value})</span>
              <div style="font-size: 0.75rem; color: var(--text-muted);">${anom.created_at || 'Just now'}</div>
            </div>
          </div>
          
          <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color);">
            <div style="font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 0.5rem;">
              Status: <span style="color: var(--accent-green);">${anom.status}</span> • Score: ${anom.anomaly_score.toFixed(4)}
            </div>
          </div>
        </div>
      `).join('');

    } catch (err: any) {
      const listContainer = document.getElementById('anomalies-list-container');
      if (listContainer) {
        listContainer.innerHTML = `<div class="card alert-error"><p>Failed to load anomalies: ${err.message}</p></div>`;
      }
    }
  }
}
