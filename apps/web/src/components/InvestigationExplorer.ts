/**
 * RevPilot AI — Investigation Explorer Component
 * Renders active investigations and workflow execution progress.
 */

import { apiClient } from '../api/client';
import { InvestigationRecord } from '../api/types';

export class InvestigationExplorerComponent {
  private container: HTMLElement;

  constructor(containerId: string) {
    const el = document.getElementById(containerId);
    if (!el) throw new Error(`Element #${containerId} not found`);
    this.container = el;
  }

  async render(): Promise<void> {
    this.container.innerHTML = `
      <div class="card" style="margin-bottom: 1.5rem;">
        <h2 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem;">Active Temporal Investigations</h2>
        <p style="color: var(--text-muted); font-size: 0.875rem;">
          Durable workflow DAGs executing autonomous evidence retrieval and causal study formulation.
        </p>
      </div>
      <div id="investigations-list-container">
        <p style="color: var(--text-muted); font-size: 0.875rem;">Loading active investigations...</p>
      </div>
    `;

    try {
      const response = await apiClient.getInvestigations();
      const listContainer = document.getElementById('investigations-list-container');
      if (!listContainer) return;

      if (!response.items || response.items.length === 0) {
        listContainer.innerHTML = '<p style="color: var(--text-muted);">No active investigations currently executing.</p>';
        return;
      }

      listContainer.innerHTML = response.items.map((inv: InvestigationRecord) => `
        <div class="card" style="margin-bottom: 1rem; border-left: 4px solid var(--accent-blue);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
              <span class="badge badge-primary">${inv.status}</span>
              <span style="font-family: monospace; font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem;">${inv.id}</span>
              <h3 style="font-size: 1.125rem; font-weight: 600; margin-top: 0.25rem;">${inv.metric_name}</h3>
            </div>
            <div style="text-align: right;">
              <span style="font-size: 0.875rem; color: var(--text-muted);">Budget: $${inv.cost_budget_usd.toFixed(2)} | Spent: $${inv.spent_usd.toFixed(2)}</span>
              <div style="font-size: 0.75rem; color: var(--text-muted);">${inv.created_at || 'Recently'}</div>
            </div>
          </div>
        </div>
      `).join('');

    } catch (err: any) {
      const listContainer = document.getElementById('investigations-list-container');
      if (listContainer) {
        listContainer.innerHTML = `<div class="card alert-error"><p>Failed to load investigations: ${err.message}</p></div>`;
      }
    }
  }
}
