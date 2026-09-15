import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';


export interface FormStatisticOption {
  id: string;
  label: string;
  count: number;
  percentage: number;
}

export interface FormStatisticQuestion {
  id: string;
  title: string;
  type: string;
  required: boolean;
  responseCount: number;
  missingCount: number;
  options: FormStatisticOption[];
  numberSummary: {
    minimum: number;
    maximum: number;
    average: number;
  } | null;
}

export interface FormStatistic {
  id: number;
  title: string;
  version: number;
  settled: boolean;
  settlementAt: string | null;
  settledAt: string | null;
  finalizedAt: string | null;
  submissionCount: number;
  historicalSubmissionCount: number;
  questionCount: number;
  questions: FormStatisticQuestion[];
}

export interface FormStatisticsResponse {
  generatedAt: string;
  summary: {
    totalForms: number;
    openForms: number;
    settledForms: number;
    totalSubmissions: number;
    uniqueRespondents: number;
  };
  forms: FormStatistic[];
}

@Injectable({ providedIn: 'root' })
export class FormStatisticsService {
  constructor(private apiService: ApiService) {}

  getStatistics(): Observable<FormStatisticsResponse> {
    return this.apiService.get<FormStatisticsResponse>(
      '/superadmin/form-statistics',
      this.apiService.createAuthHeaders()
    );
  }
}
