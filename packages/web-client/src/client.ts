/**
 * RevPilot AI — API Client SDK
 * Conforms to:
 * - docs/26-api/API-STANDARDS.md
 * - INV-ACT-003 (Zero Agent Self-Approval)
 * - INV-TEN-001..003 (Tenant Scoping)
 */

import {
  AnomalyRecord,
  ApprovalRequestRecord,
  KillSwitchRequest,
  UserPrincipal,
} from "./types.js";
import { verifyApprovalRecordDigest } from "./digest.js";

export interface ClientOptions {
  baseUrl?: string;
  authToken?: string;
}

export class RevPilotClient {
  private baseUrl: string;
  private authToken?: string;

  constructor(options: ClientOptions = {}) {
    this.baseUrl = options.baseUrl || "http://localhost:8000";
    this.authToken = options.authToken;
  }

  public setAuthToken(token: string): void {
    this.authToken = token;
  }

  private getHeaders(): HeadersInit {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Correlation-ID": `corr_web_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`,
    };
    if (this.authToken) {
      headers["Authorization"] = `Bearer ${this.authToken}`;
    }
    return headers;
  }

  public async getHealthLive(): Promise<{ status: string }> {
    const res = await fetch(`${this.baseUrl}/health/live`);
    if (!res.ok) throw new Error(`Liveness probe failed: ${res.statusText}`);
    return res.json();
  }

  public async getHealthReady(): Promise<{ status: string; checks: Record<string, string> }> {
    const res = await fetch(`${this.baseUrl}/health/ready`);
    if (!res.ok) throw new Error(`Readiness probe failed: ${res.statusText}`);
    return res.json();
  }

  /**
   * Signs and approves an action request.
   * STRICT ENFORCEMENT: Only authenticated human principals can approve (INV-ACT-003).
   */
  public async approveAction(
    approvalId: string,
    signer: UserPrincipal,
    expectedDigest: string,
    comments?: string
  ): Promise<{ status: string; approval_id: string }> {
    // Invariant Check (INV-ACT-003)
    if (!signer.is_human) {
      throw new Error(
        "ERR_AGENT_SELF_APPROVAL: AI agents and autonomous planners cannot approve actions (INV-ACT-003)."
      );
    }

    if (!expectedDigest || expectedDigest.trim() === "") {
      throw new Error("ERR_MISSING_DIGEST: Approval requires valid cryptographic payload digest.");
    }

    const payload = {
      signer_id: signer.principal_id,
      expected_payload_digest: expectedDigest,
      comments: comments || "Approved by authenticated human operator",
    };

    const res = await fetch(`${this.baseUrl}/api/v1/approvals/${approvalId}/approve`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.message || `Approval failed with status ${res.status}`);
    }

    return res.json();
  }

  /**
   * Rejects an approval request.
   */
  public async rejectAction(
    approvalId: string,
    reason: string
  ): Promise<{ status: string; approval_id: string }> {
    const res = await fetch(`${this.baseUrl}/api/v1/approvals/${approvalId}/reject`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ reason }),
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.message || `Rejection failed with status ${res.status}`);
    }

    return res.json();
  }

  /**
   * Activates emergency safety kill switch (< 500ms propagation).
   */
  public async activateKillSwitch(req: KillSwitchRequest): Promise<{ status: string; latency_ms: number }> {
    const res = await fetch(`${this.baseUrl}/api/v1/actions/kill-switch`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(req),
    });

    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.message || `Kill switch failed with status ${res.status}`);
    }

    return res.json();
  }
}
