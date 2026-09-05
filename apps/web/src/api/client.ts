/**
 * RevPilot AI — Production REST API Client
 * Replaces hardcoded mock arrays with live HTTP communication.
 */

import { AuthManager } from '../auth/token';
import {
  AnomalyRecord,
  AnomalyListResponse,
  ApprovalListResponse,
  ApprovalRequestRecord,
  InvestigationRecord,
  KillSwitchResponse,
} from './types';

export class RevPilotApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = '') {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      ...AuthManager.getHeaders(),
      ...(options.headers as Record<string, string> || {}),
    };

    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      let errorMsg = `HTTP ${response.status} ${response.statusText}`;
      try {
        const errJson = await response.json();
        errorMsg = errJson.message || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  async getAnomalies(status?: string, limit: number = 50): Promise<AnomalyListResponse> {
    const query = new URLSearchParams();
    if (status) query.append('status', status);
    query.append('limit', limit.toString());
    return this.request<AnomalyListResponse>(`/api/v1/analytics/anomalies?${query.toString()}`);
  }

  async getAnomalyDetail(anomalyId: string): Promise<AnomalyRecord> {
    return this.request<AnomalyRecord>(`/api/v1/analytics/anomalies/${anomalyId}`);
  }

  async getApprovals(): Promise<ApprovalListResponse> {
    return this.request<ApprovalListResponse>('/api/v1/approvals');
  }

  async approveAction(approvalId: string, digest?: string): Promise<any> {
    return this.request(`/api/v1/approvals/${approvalId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ expected_payload_digest: digest }),
    });
  }

  async rejectAction(approvalId: string, reason: string): Promise<any> {
    return this.request(`/api/v1/approvals/${approvalId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  async dryRunAction(approvalId: string): Promise<any> {
    return this.request('/api/v1/actions/dry-run', {
      method: 'POST',
      body: JSON.stringify({
        approval_id: approvalId,
        idempotency_key: `dryrun_${Date.now()}`,
      }),
    });
  }

  async engageKillSwitch(scope: string, reason: string): Promise<KillSwitchResponse> {
    return this.request<KillSwitchResponse>('/api/v1/actions/kill-switch', {
      method: 'POST',
      body: JSON.stringify({ scope, reason }),
    });
  }

  async getInvestigations(): Promise<{ items: InvestigationRecord[]; count: number }> {
    return this.request<{ items: InvestigationRecord[]; count: number }>('/api/v1/investigations');
  }
}

export const apiClient = new RevPilotApiClient();
