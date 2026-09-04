/**
 * RevPilot AI — Cryptographic Payload Digest Binding
 * Conforms to DEC-009, ADR-0012, AC-008, and INV-ACT-002.
 * Calculates deterministic SHA-256 digest over approval payload parameters.
 */

import { ApprovalRequestRecord } from "./types.js";

/**
 * Deterministically sorts object keys for canonical JSON serialization.
 */
function canonicalizeJson(obj: unknown): string {
  if (obj === null || typeof obj !== "object") {
    return JSON.stringify(obj);
  }
  if (Array.isArray(obj)) {
    return "[" + obj.map(canonicalizeJson).join(",") + "]";
  }
  const keys = Object.keys(obj as Record<string, unknown>).sort();
  const pairs = keys.map((k) => `"${k}":${canonicalizeJson((obj as Record<string, unknown>)[k])}`);
  return "{" + pairs.join(",") + "}";
}

/**
 * Computes deterministic SHA-256 digest string for an approval request.
 * Uses Web Crypto API if available, otherwise Node.js crypto.
 */
export async function computeApprovalDigest(
  tenantId: string,
  actionType: string,
  payload: Record<string, unknown>,
  targetEntities: string[],
  estimatedCostUsd: number,
  policyVersion: string,
  expiresAt: string
): Promise<string> {
  const sortedTargets = [...targetEntities].sort();
  const canonicalPayload = canonicalizeJson(payload);

  const rawMessage = [
    tenantId,
    actionType,
    canonicalPayload,
    sortedTargets.join(","),
    estimatedCostUsd.toFixed(2),
    policyVersion,
    expiresAt,
  ].join("|");

  const msgBuffer = new TextEncoder().encode(rawMessage);

  if (typeof crypto !== "undefined" && crypto.subtle) {
    const hashBuffer = await crypto.subtle.digest("SHA-256", msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  // Node.js fallback
  try {
    const nodeCrypto = await import("crypto");
    return nodeCrypto.createHash("sha256").update(msgBuffer).digest("hex");
  } catch {
    throw new Error("Cryptographic environment not available for SHA-256 digest computation.");
  }
}

/**
 * Verifies that the record digest matches the computed digest.
 * Returns true only if the digest matches and has not been tampered with.
 */
export async function verifyApprovalRecordDigest(record: ApprovalRequestRecord): Promise<boolean> {
  if (!record.payload_digest || record.payload_digest.trim() === "") {
    return false;
  }
  const expected = await computeApprovalDigest(
    record.tenant_id,
    record.action_type,
    record.payload,
    record.target_entities,
    record.estimated_cost_usd,
    record.policy_version,
    record.expires_at
  );
  return record.payload_digest.toLowerCase() === expected.toLowerCase();
}
