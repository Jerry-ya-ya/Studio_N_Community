import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export type AuditLogStatus = 'success' | 'pending' | 'notice';

export interface AuditLogItem {
  id?: string;
  actor: string;
  action: string;
  target: string;
  time: string;
  status: AuditLogStatus;
  ip?: string;
  rawJson?: Record<string, unknown> | null;
  raw_json?: Record<string, unknown> | null;
  raw?: string;
}

export interface AuditLogResponse {
  type: string;
  path: string;
  count: number;
  items: AuditLogItem[];
}

@Injectable({
  providedIn: 'root'
})
export class AuditLogService {
  constructor(private apiService: ApiService) {}

  getRegisterLogs(limit = 50): Observable<AuditLogResponse> {
    const cacheBuster = Date.now();
    const headers = this.apiService.createAuthHeaders()
      .set('Cache-Control', 'no-cache')
      .set('Pragma', 'no-cache');

    return this.apiService.get<AuditLogResponse>(
      `/superadmin/logs/register?limit=${limit}&_=${cacheBuster}`,
      headers
    );
  }
}
