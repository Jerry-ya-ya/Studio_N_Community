import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface ScheduleBlockDto {
  id: number;
  column: number;
  startRow: number;
  span: number;
  title: string;
}

export interface ScheduleResponse {
  blocks: ScheduleBlockDto[];
  updatedAt?: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class ScheduleService {
  constructor(private apiService: ApiService) {}

  getSchedule(): Observable<ScheduleResponse> {
    return this.apiService.get<ScheduleResponse>('/schedule', this.apiService.createAuthHeaders());
  }

  saveSchedule(blocks: ScheduleBlockDto[]): Observable<ScheduleResponse> {
    return this.apiService.put<ScheduleResponse>('/schedule', { blocks }, this.apiService.createAuthHeaders());
  }
}
