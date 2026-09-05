/**
 * RevPilot AI — Human Approval Center Component
 * Conforms to:
 * - docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3..§4
 * - docs/28-frontend/FRONTEND-SPEC.md
 * - Strict Invariant: Zero Agent Self-Approval (INV-ACT-003)
 */

import { apiClient } from '../api/client';
import { ApprovalRequestRecord } from '../api/types';

export class ApprovalCenterComponent {
  private container: HTMLElement;

  constructor(containerId: string) {
    const el = document.getElementById(containerId);
    if (!el) throw new Error(`Element #${containerId} not found`);
    this.container = el;
  }

  public async render(): Promise<void> {
    this.container.innerHTML = `
      <div class="card" style="margin-bottom: 1.5rem;">
        <h2 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.5rem;">Pending Human Approvals</h2>
        <p style="color: var(--text-muted); font-size: 0.875rem;">
          Mutations exceeding policy authority tiers require cryptographically verified human operator signatures.
        </p>
      </div>
      <div id="approvals-cards-container">
        <p style="color: var(--text-muted); font-size: 0.875rem;">Loading approvals queue...</p>
      </div>
    `;

    try {
      const response = await apiClient.getApprovals();
      const listContainer = document.getElementById('approvals-cards-container');
      if (!listContainer) return;

      if (!response.items || response.items.length === 0) {
        listContainer.innerHTML = '<p style="color: var(--text-muted);">No pending approvals in queue.</p>';
        return;
      }

      listContainer.innerHTML = response.items.map((item: ApprovalRequestRecord) => `
        <div class="card" id="card-${item.id}" style="margin-bottom: 1.5rem; border-left: 4px solid var(--accent-orange);">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
            <div>
              <span class="badge badge-warning">${item.required_approval_tier}</span>
              <span style="font-family: monospace; font-size: 0.75rem; color: var(--text-muted); margin-left: 0.5rem;">${item.id}</span>
              <h3 style="font-size: 1.125rem; font-weight: 600; margin-top: 0.25rem;">${item.action_type}</h3>
            </div>
            <div style="text-align: right;">
              <span style="font-size: 1.125rem; font-weight: 700; color: var(--text-main);">$${(item.cost_usd || item.estimated_cost_usd || 0).toLocaleString()}</span>
              <div style="font-size: 0.75rem; color: var(--text-muted);">Expires: ${item.expires_in || '24h'}</div>
            </div>
          </div>

          <div style="background-color: var(--bg-card); padding: 0.75rem; border-radius: 4px; font-family: monospace; font-size: 0.75rem; margin-bottom: 1rem; border: 1px solid var(--border-color);">
            <div style="color: var(--text-muted);">Target Entities: ${(item.target_entity_refs || []).join(', ')}</div>
            <div style="color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              Payload Digest: ${item.digest || item.payload_digest || 'sha256:verified_digest'}
            </div>
          </div>

          <div style="display: flex; gap: 0.75rem; justify-content: flex-end;" id="actions-${item.id}">
            <button class="btn btn-outline btn-dryrun" data-id="${item.id}">Execute Dry-Run</button>
            <button class="btn btn-danger btn-reject" data-id="${item.id}">Reject</button>
            <button class="btn btn-primary btn-approve" data-id="${item.id}" data-digest="${item.digest || item.payload_digest}">Sign & Grant Approval</button>
          </div>
        </div>
      `).join('');

      this.bindEvents();

    } catch (err: any) {
      const listContainer = document.getElementById('approvals-cards-container');
      if (listContainer) {
        listContainer.innerHTML = `<div class="card alert-error"><p>Failed to load approvals: ${err.message}</p></div>`;
      }
    }
  }

  private bindEvents(): void {
    // Approve
    this.container.querySelectorAll('.btn-approve').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const target = e.currentTarget as HTMLButtonElement;
        const id = target.getAttribute('data-id');
        const digest = target.getAttribute('data-digest') || '';
        if (!id) return;

        target.disabled = true;
        target.innerText = 'Signing...';

        try {
          await apiClient.approveAction(id, digest);
          const card = document.getElementById(`card-${id}`);
          if (card) {
            card.style.borderLeftColor = 'var(--accent-green)';
            const actionsDiv = document.getElementById(`actions-${id}`);
            if (actionsDiv) {
              actionsDiv.innerHTML = '<span style="color: var(--accent-green); font-weight: 600; font-size: 0.875rem;">✓ Approved & Cryptographically Signed</span>';
            }
          }
        } catch (err: any) {
          alert(`Approval failed: ${err.message}`);
          target.disabled = false;
          target.innerText = 'Sign & Grant Approval';
        }
      });
    });

    // Reject
    this.container.querySelectorAll('.btn-reject').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const target = e.currentTarget as HTMLButtonElement;
        const id = target.getAttribute('data-id');
        if (!id) return;

        const reason = prompt('Enter rejection reason:') || 'Rejected by operator';
        target.disabled = true;

        try {
          await apiClient.rejectAction(id, reason);
          const card = document.getElementById(`card-${id}`);
          if (card) {
            card.style.borderLeftColor = 'var(--accent-red)';
            const actionsDiv = document.getElementById(`actions-${id}`);
            if (actionsDiv) {
              actionsDiv.innerHTML = `<span style="color: var(--accent-red); font-size: 0.875rem;">✗ Rejected (${reason})</span>`;
            }
          }
        } catch (err: any) {
          alert(`Rejection failed: ${err.message}`);
          target.disabled = false;
        }
      });
    });

    // Dry-run
    this.container.querySelectorAll('.btn-dryrun').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const target = e.currentTarget as HTMLButtonElement;
        const id = target.getAttribute('data-id');
        if (!id) return;

        target.disabled = true;
        target.innerText = 'Simulating...';

        try {
          const res = await apiClient.dryRunAction(id);
          alert(`Dry Run Result: ${res.status}\nExternal Side Effects: ${res.external_side_effects}`);
        } catch (err: any) {
          alert(`Dry Run failed: ${err.message}`);
        } finally {
          target.disabled = false;
          target.innerText = 'Execute Dry-Run';
        }
      });
    });
  }
}
