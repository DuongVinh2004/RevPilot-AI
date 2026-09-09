/**
 * RevPilot AI — Frontend Authentication Context & Token Manager
 */

export class AuthManager {
  private static tokenKey = 'revpilot_auth_token';
  private static devPrincipalKey = 'revpilot_dev_principal';
  private static devTenantKey = 'revpilot_dev_tenant';

  static getToken(): string | null {
    return localStorage.getItem(this.tokenKey) || 'revpilot_dev_token_secret_2026';
  }

  static setToken(token: string): void {
    localStorage.setItem(this.tokenKey, token);
  }

  static getDevPrincipal(): string {
    return localStorage.getItem(this.devPrincipalKey) || 'usr_admin_001';
  }

  static getDevTenant(): string {
    return localStorage.getItem(this.devTenantKey) || 'tnt_dev_001';
  }

  static getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if ((import.meta as any).env?.DEV && (import.meta as any).env?.VITE_ALLOW_DEV_AUTH === 'true') {
      headers['X-Dev-Principal'] = this.getDevPrincipal();
      headers['X-Dev-Tenant'] = this.getDevTenant();
    }
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
  }
}
