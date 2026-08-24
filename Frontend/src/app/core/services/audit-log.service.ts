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
    return this.getLogs('/admin/logs/register', limit);
  }

  getProjectLogs(limit = 50): Observable<AuditLogResponse> {
    return this.getLogs('/admin/logs/project', limit);
  }

  getSignInLogs(limit = 50): Observable<AuditLogResponse> {
    return this.getLogs('/admin/logs/sign-in', limit);
  }

  getContentLogs(limit = 50): Observable<AuditLogResponse> {
    return this.getLogs('/superadmin/logs/content', limit);
  }

  getNewsLogs(limit = 50): Observable<AuditLogResponse> {
    return this.getLogs('/superadmin/logs/news', limit);
  }

  getTodoSettlementLogs(limit = 50): Observable<AuditLogResponse> {
    return this.getLogs('/superadmin/logs/todo-settlement', limit);
  }

  private getLogs(endpoint: string, limit: number): Observable<AuditLogResponse> {
    const cacheBuster = Date.now();
    const headers = this.apiService.createAuthHeaders()
      .set('Cache-Control', 'no-cache')
      .set('Pragma', 'no-cache');

    return this.apiService.get<AuditLogResponse>(
      `${endpoint}?limit=${limit}&_=${cacheBuster}`,
      headers
    );
  }
}
