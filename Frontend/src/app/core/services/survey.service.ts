import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';
import { FormSchema } from './form-builder.service';


export type SurveyAnswer = string | number | boolean | string[] | null;

export interface SurveyForm {
  id: number;
  title: string;
  description: string;
  schema: FormSchema;
  version: number;
  settlementAt: string | null;
  settledAt: string | null;
  settled: boolean;
  submitted: boolean;
  submittedAt: string | null;
  updated_at?: string | null;
}

export interface SurveySubmission {
  id: number;
  formId: number;
  formVersion: number;
  submittedAt: string;
}

@Injectable({ providedIn: 'root' })
export class SurveyService {
  constructor(private apiService: ApiService) {}

  listForms(): Observable<SurveyForm[]> {
    return this.apiService.get<SurveyForm[]>(
      '/forms', this.apiService.createAuthHeaders()
    );
  }

  submit(
    formId: number,
    formVersion: number,
    answers: Record<string, SurveyAnswer>
  ): Observable<SurveySubmission> {
    return this.apiService.post<SurveySubmission>(
      `/forms/${formId}/submissions`,
      { formVersion, answers },
      this.apiService.createAuthHeaders()
    );
  }
}
