import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface CheckInStatus {
  checkedInToday: boolean;
  today: string;
  todayPoints: number;
  isWeekend: boolean;
  totalPoints: number;
  lastCheckIn: string | null;
  earnedPoints?: number;
  message?: string;
}

@Injectable({
  providedIn: 'root'
})
export class CheckInService {
  constructor(private apiService: ApiService) {}

  getStatus(): Observable<CheckInStatus> {
    return this.apiService.get<CheckInStatus>('/check-in/status', this.apiService.createAuthHeaders());
  }

  checkIn(): Observable<CheckInStatus> {
    return this.apiService.post<CheckInStatus>('/check-in', {}, this.apiService.createAuthHeaders());
  }
}
