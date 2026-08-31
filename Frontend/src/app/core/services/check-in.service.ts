import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface CheckInStatus {
  checkedInToday: boolean;
  today: string;
  todayPoints: number;
  isWeekend: boolean;
  totalPoints: number;
  lastSevenDays: {
    checkedDays: number;
    totalDays: number;
    days: {
      date: string;
      checked: boolean;
      points: number;
    }[];
  };
  lastCheckIn: string | null;
  earnedPoints?: number;
  message?: string;
}

export interface CheckInHistory {
  year: number;
  checkedDates: string[];
  availableYears: number[];
}

@Injectable({
  providedIn: 'root'
})
export class CheckInService {
  constructor(private apiService: ApiService) {}

  getStatus(): Observable<CheckInStatus> {
    return this.apiService.get<CheckInStatus>('/check-in/status', this.apiService.createAuthHeaders());
  }

  getHistory(year: number): Observable<CheckInHistory> {
    return this.apiService.get<CheckInHistory>(`/check-in/history?year=${year}`, this.apiService.createAuthHeaders());
  }

  checkIn(): Observable<CheckInStatus> {
    return this.apiService.post<CheckInStatus>('/check-in', {}, this.apiService.createAuthHeaders());
  }
}
