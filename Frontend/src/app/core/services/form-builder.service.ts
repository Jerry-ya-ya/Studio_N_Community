import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';


export type FormQuestionType =
  | 'short_text'
  | 'long_text'
  | 'single_choice'
  | 'multiple_choice'
  | 'dropdown'
  | 'number'
  | 'date'
  | 'boolean';

export interface FormOption {
  id: string;
  label: string;
}

export interface FormQuestion {
  id: string;
  type: FormQuestionType;
  title: string;
  description: string;
  required: boolean;
  options: FormOption[];
}

export interface FormSchema {
  schemaVersion: 1;
  questions: FormQuestion[];
}

export interface AdminForm {
  id: number;
  title: string;
  description: string;
  schema: FormSchema;
  version: number;
  settlementAt: string | null;
  settledAt: string | null;
  settled: boolean;
  createdBy?: string | null;
  created_by_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CreateFormPayload {
  title: string;
  description: string;
  schema: FormSchema;
  settlementAt: string | null;
}

export interface UpdateFormPayload extends CreateFormPayload {
  version: number;
}

@Injectable({ providedIn: 'root' })
export class FormBuilderService {
  constructor(private apiService: ApiService) {}

  listForms(): Observable<AdminForm[]> {
    return this.apiService.get<AdminForm[]>(
      '/admin/forms',
      this.apiService.createAuthHeaders()
    );
  }

  createForm(payload: CreateFormPayload): Observable<AdminForm> {
    return this.apiService.post<AdminForm>(
      '/admin/forms',
      payload,
      this.apiService.createAuthHeaders()
    );
  }

  updateForm(formId: number, payload: UpdateFormPayload): Observable<AdminForm> {
    return this.apiService.put<AdminForm>(
      `/admin/forms/${formId}`,
      payload,
      this.apiService.createAuthHeaders()
    );
  }

  settleForm(formId: number): Observable<AdminForm> {
    return this.apiService.post<AdminForm>(
      `/admin/forms/${formId}/settle`,
      {},
      this.apiService.createAuthHeaders()
    );
  }

  deleteForm(formId: number): Observable<{ message: string; id: number }> {
    return this.apiService.delete<{ message: string; id: number }>(
      `/admin/forms/${formId}`,
      this.apiService.createAuthHeaders()
    );
  }
}
