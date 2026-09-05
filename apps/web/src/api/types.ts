/**
 * RevPilot AI — API Response & Domain Entity Types
 * Strict typing for frontend-backend communication.
 */

export interface Citation {
  id: string;
  source: string;
  classification: string;
  summary: string;
  date?: string;
  hash?: string;
}

export interface AnomalyRecord {
  id: string;
  tenant_id?: string;
  metric_id: string;
  actual_value: number;
  expected_value: number;
  anomaly_score: number;
  severity: 'CRITICAL' | 'HIGH' | 'MAJOR' | 'MINOR' | 'INFORMATIONAL';
  status: 'DETECTED' | 'VALIDATED' | 'LOCALIZED' | 'ACKNOWLEDGED' | 'RESOLVED';
  created_at: string;
  citations?: Citation[];
}

export interface AnomalyListResponse {
  items: AnomalyRecord[];
  count: number;
  limit: number;
  offset: number;
}

export interface ApprovalRequestRecord {
  id: string;
  tenant_id?: string;
  action_type: string;
  target_entity_refs: string[];
  cost_usd: number;
  estimated_cost_usd?: number;
  required_approval_tier: 'TIER_1' | 'TIER_2' | 'TIER_3';
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXECUTING' | 'COMPLETED';
  digest?: string;
  payload_digest?: string;
  policy_digest?: string;
  expires_in?: string;
  expiry_time?: string;
  created_at?: string;
}

export interface ApprovalListResponse {
  items: ApprovalRequestRecord[];
  count: number;
}

export interface InvestigationRecord {
  id: string;
  tenant_id: string;
  status: string;
  metric_name: string;
  cost_budget_usd: number;
  spent_usd: number;
  created_at: string;
}

export interface KillSwitchResponse {
  status: string;
  kill_switch_id: string;
  scope: string;
  reason: string;
  activated_by: string;
  propagation_latency_ms: number;
}
