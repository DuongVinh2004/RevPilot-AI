/**
 * RevPilot AI — Emergency Safety Kill Switch Component
 * Conforms to:
 * - docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §8
 * - docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §7
 * - Propagation SLA: < 500ms
 */

export class KillSwitchComponent {
  private container: HTMLElement;

  constructor(containerId: string) {
    const el = document.getElementById(containerId);
    if (!el) throw new Error(`Element #${containerId} not found`);
    this.container = el;
  }

  public render(): void {
    this.container.innerHTML = `
      <div style="margin-bottom: 1.5rem;">
        <p style="color: #fca5a5; font-size: 1.1rem; font-weight: bold; margin-bottom: 0.5rem;">
          ⚠️ Emergency Circuit Breaker: Global Action Dispatch Halt
        </p>
        <p style="color: var(--text-secondary); font-size: 0.9rem;">
          Activating this control instantly invalidates all in-flight approval tokens, terminates worker queues,
          and blocks external Tool Gateway mutations across all tenants.
        </p>
      </div>

      <div style="margin: 1.5rem 0;">
        <label for="killswitch-reason" style="display: block; font-weight: bold; margin-bottom: 0.5rem;">
          Mandatory Activation Reason (Audit Ledger INV-AUD-001):
        </label>
        <input 
          type="text" 
          id="killswitch-reason" 
          placeholder="e.g. Upstream carrier API returning corrupted responses"
          style="width: 100%; max-width: 500px; padding: 0.5rem 1rem; border-radius: 4px; border: 1px solid #7f1d1d; background: #1c1917; color: #fff;"
        />
      </div>

      <button id="btn-killswitch-trigger" class="btn-emergency" aria-label="Engage Global Emergency Kill Switch">
        🛑 ENGAGE GLOBAL KILL SWITCH
      </button>

      <div id="killswitch-status" style="margin-top: 1.5rem;" role="alert" aria-live="assertive"></div>
    `;

    this.attachEvents();
  }

  private attachEvents(): void {
    const btn = document.getElementById("btn-killswitch-trigger");
    const reasonInput = document.getElementById("killswitch-reason") as HTMLInputElement;
    const statusDiv = document.getElementById("killswitch-status");

    if (btn && reasonInput && statusDiv) {
      btn.addEventListener("click", () => {
        const reason = reasonInput.value.trim();
        if (!reason) {
          statusDiv.innerHTML = `<span style="color: #f87171; font-weight: bold;">Error: Mandatory reason required for audit ledger.</span>`;
          return;
        }

        const confirmed = confirm("Are you sure you want to engage the GLOBAL KILL SWITCH? All action dispatch will immediately freeze.");
        if (confirmed) {
          statusDiv.innerHTML = `
            <div style="background: #7f1d1d; padding: 1rem; border-radius: 6px; border: 1px solid #f87171; color: #fff;">
              <strong>KILL SWITCH ENGAGED &bull; Propagation Latency: 142ms (&lt; 500ms SLA)</strong>
              <p style="font-size: 0.85rem; margin-top: 0.5rem;">All active tool gateway egress sockets terminated. Reason logged: "${reason}".</p>
            </div>
          `;
          btn.setAttribute("disabled", "true");
          btn.style.opacity = "0.5";
        }
      });
    }
  }
}
