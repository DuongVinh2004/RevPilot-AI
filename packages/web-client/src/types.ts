/**
 * RevPilot AI — Web Client Domain Types and Contracts
 * Conforms to:
 * - docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md
 * - docs/28-frontend/FRONTEND-SPEC.md
 * - docs/26-api/API-STANDARDS.md
 * - INV-ACT-001..003, INV-TEN-001..003
 */

export enum ApprovalStatus {
  DRAFT = "DRAFT",
  PENDING = "PENDING",
  APPROVED = "APPROVED",
  REJECTED = "REJECTED",
  AMENDED = "AMENDED",
  EXPIRED = "EXPIRED",
  REVOKED = "REVOKED",
  SUPERSEDED = "SUPERSEDED",
  EXECUTING = "EXECUTING",
  COMPLETED = "COMPLETED",
  UNKNOWN = "UNKNOWN",
  RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED",
}

export enum ApprovalTier {
  TIER_1 = "TIER_1", // Operational, Low Cost (< $1,000)
  TIER_2 = "TIER_2", // Tactical, Moderate Cost ($1,000 - $10,000)
  TIER_3 = "TIER_3", // Strategic, High Impact (> $10,000 or contract modification)
}

export interface ApprovalRequestRecord {
  approval_id: string;
  tenant_id: string;
  decision_id: string;
  action_type: string;
  target_entities: string[];
  payload: Record<string, unknown>;
  estimated_cost_usd: number;
  currency: string;
  policy_version: string;
  payload_digest: string; // Cryptographic SHA-256 seal
  status: ApprovalStatus;
  required_tier: ApprovalTier;
  created_at: string;
  expires_at: string;
  approved_by?: string;
  approved_at?: string;
  rejection_reason?: string;
}

export interface EvidenceCitation {
  citation_id: string;
  source: string;
  effective_date: string;
  classification: "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "RESTRICTED";
  summary: string;
  provenance_hash: string;
}

export interface AnomalyRecord {
  anomaly_id: string;
  tenant_id: string;
  metric_name: string;
  current_value: number;
  expected_value: number;
  deviation_percentage: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  detected_at: string;
  status: "OPEN" | "INVESTIGATING" | "RESOLVED" | "SUPPRESSED";
  citations: EvidenceCitation[];
}

export interface UserPrincipal {
  principal_id: string;
  tenant_id: string;
  email: string;
  roles: string[];
  is_human: boolean; // INV-ACT-003: Must be true to sign approval requests
}

export interface KillSwitchRequest {
  scope: "GLOBAL" | "TENANT" | "CAPABILITY";
  target_id?: string;
  reason: string;
}
