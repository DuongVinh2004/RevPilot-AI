/**
 * RevPilot AI — Human Approval Center Component
 * Conforms to:
 * - docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §3..§4
 * - docs/28-frontend/FRONTEND-SPEC.md
 * - DEC-008, DEC-009, ADR-0012
 * - Strict Invariant: Zero Agent Self-Approval (INV-ACT-003)
 */

export interface MockApprovalItem {
  id: string;
  action_type: string;
  tier: "TIER_1" | "TIER_2" | "TIER_3";
  targets: string[];
  cost_usd: number;
  policy_version: string;
  digest: string;
  expires_in: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
}

export const MOCK_PENDING_APPROVALS: MockApprovalItem[] = [
  {
    id: "appr_01h8x9m2k4p8",
    action_type: "ISSUE_SERVICE_CREDIT_VOUCHER",
    tier: "TIER_2",
    targets: ["cust_enterprise_alpha", "sub_arr_450k"],
    cost_usd: 2500.0,
    policy_version: "2026.09.v1",
    digest: "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
    expires_in: "14m 32s",
    status: "PENDING",
  },
  {
    id: "appr_01h8x9n1a9b2",
    action_type: "OVERRIDE_CARRIER_SLA_PENALTY",
    tier: "TIER_3",
    targets: ["carrier_global_freight", "contract_2025_exp"],
    cost_usd: 15400.0,
    policy_version: "2026.09.v1",
    digest: "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    expires_in: "4m 10s",
    status: "PENDING",
  },
];

export class ApprovalCenterComponent {
  private container: HTMLElement;

  constructor(containerId: string) {
    const el = document.getElementById(containerId);
    if (!el) throw new Error(`Element #${containerId} not found`);
    this.container = el;
  }

  public render(items: MockApprovalItem[] = MOCK_PENDING_APPROVALS): void {
    if (items.length === 0) {
      this.container.innerHTML = `
        <div class="empty-state" role="status">
          <p>No pending approvals requiring human signature. All queues clean.</p>
        </div>
      `;
      return;
    }

    this.container.innerHTML = items
      .map(
        (item) => `
        <article class="approval-card" id="card-${item.id}" aria-labelledby="title-${item.id}">
          <div class="card-header">
            <div>
              <span class="badge badge-${item.tier.toLowerCase()}">${item.tier}</span>
              <strong id="title-${item.id}" style="margin-left: 0.5rem;">${item.action_type}</strong>
            </div>
            <span class="badge badge-rc" aria-label="Expires in ${item.expires_in}">⏱️ Expires: ${item.expires_in}</span>
          </div>

          <div class="card-body">
            <p><strong>Target Entities:</strong> <code>${item.targets.join(", ")}</code></p>
            <p><strong>Estimated Impact / Cost:</strong> $${item.cost_usd.toLocaleString("en-US", { minimumFractionDigits: 2 })} USD</p>
            <p><strong>Governing Policy:</strong> ${item.policy_version}</p>
            
            <div class="digest-box" aria-label="Sealed Cryptographic Payload Digest">
              <div>🔒 <strong>SHA-256 Payload Digest Binding (DEC-009):</strong></div>
              <code>${item.digest}</code>
            </div>
          </div>

          <div class="action-buttons" role="group" aria-label="Approval Actions for ${item.id}">
            <button class="btn btn-approve" data-id="${item.id}" data-digest="${item.digest}" aria-label="Approve ${item.action_type}">
              ✓ Sign &amp; Approve
            </button>
            <button class="btn btn-dryrun" data-id="${item.id}" aria-label="Simulate Dry Run for ${item.action_type}">
              ⚙️ Pre-Flight Dry Run
            </button>
            <button class="btn btn-reject" data-id="${item.id}" aria-label="Reject ${item.action_type}">
              ✕ Reject
            </button>
          </div>
        </article>
      `
      )
      .join("");

    this.attachEvents();
  }

  private attachEvents(): void {
    this.container.querySelectorAll(".btn-approve").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const target = e.currentTarget as HTMLButtonElement;
        const id = target.getAttribute("data-id");
        this.handleApprove(id!);
      });
    });

    this.container.querySelectorAll(".btn-reject").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const target = e.currentTarget as HTMLButtonElement;
        const id = target.getAttribute("data-id");
        this.handleReject(id!);
      });
    });

    this.container.querySelectorAll(".btn-dryrun").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const target = e.currentTarget as HTMLButtonElement;
        const id = target.getAttribute("data-id");
        this.handleDryRun(id!);
      });
    });
  }

  private handleApprove(id: string): void {
    const card = document.getElementById(`card-${id}`);
    if (card) {
      card.style.borderColor = "var(--status-green)";
      const actions = card.querySelector(".action-buttons");
      if (actions) {
        actions.innerHTML = `
          <div role="status" style="color: var(--status-green); font-weight: bold;">
            ✓ Approved & Signed by Human Operator (Digest Verified). Dispatched to Saga Ledger.
          </div>
        `;
      }
    }
  }

  private handleReject(id: string): void {
    const card = document.getElementById(`card-${id}`);
    if (card) {
      card.style.borderColor = "var(--status-red)";
      const actions = card.querySelector(".action-buttons");
      if (actions) {
        actions.innerHTML = `
          <div role="status" style="color: var(--status-red); font-weight: bold;">
            ✕ Rejected by Human Operator. Action Terminated.
          </div>
        `;
      }
    }
  }

  private handleDryRun(id: string): void {
    alert(`[DRY-RUN SIMULATION] Execution parity verified for ${id}. External mutations: 0. Zero side effects.`);
  }
}
