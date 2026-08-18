import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { environment } from '../../../environments/environment';

export type ActivityVisibility = 'public' | 'private';

export interface ActivityPromotion {
  id: number;
  title: string;
  description: string;
  visibility: ActivityVisibility;
  targetFilter: string;
  target_filter?: string;
  imageUrl?: string | null;
  image_url?: string | null;
  sort_order?: number;
  createdBy?: string | null;
  created_by_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ActivityPayload {
  title: string;
  description: string;
  visibility: ActivityVisibility;
  targetFilter: string;
  sort_order?: number;
  imageUrl?: string | null;
}

@Injectable({
  providedIn: 'root'
})
export class ActivityService {
  private readonly assetBaseUrl = environment.apiUrl.replace(/\/api\/?$/, '');

  constructor(private apiService: ApiService) {}

  getPublicActivities(): Observable<ActivityPromotion[]> {
    return this.apiService.get<ActivityPromotion[]>(`/activities?_=${Date.now()}`);
  }

  getPrivateActivities(): Observable<ActivityPromotion[]> {
    return this.apiService.get<ActivityPromotion[]>(
      `/private/activities?_=${Date.now()}`,
      this.apiService.createAuthHeaders()
    );
  }

  getAdminActivities(): Observable<ActivityPromotion[]> {
    return this.apiService.get<ActivityPromotion[]>(
      '/admin/activities',
      this.apiService.createAuthHeaders()
    );
  }

  createActivity(payload: ActivityPayload): Observable<ActivityPromotion> {
    return this.apiService.post<ActivityPromotion>(
      '/admin/activities',
      payload,
      this.apiService.createAuthHeaders()
    );
  }

  updateActivity(activityId: number, payload: ActivityPayload): Observable<ActivityPromotion> {
    return this.apiService.put<ActivityPromotion>(
      `/admin/activities/${activityId}`,
      payload,
      this.apiService.createAuthHeaders()
    );
  }

  deleteActivity(activityId: number): Observable<{ message: string; id: number }> {
    return this.apiService.delete<{ message: string; id: number }>(
      `/admin/activities/${activityId}`,
      this.apiService.createAuthHeaders()
    );
  }

  uploadActivityImage(activityId: number, file: File): Observable<ActivityPromotion> {
    const formData = new FormData();
    formData.append('file', file);

    return this.apiService.post<ActivityPromotion>(
      `/admin/activities/${activityId}/image`,
      formData,
      this.apiService.createAuthHeaders()
    );
  }

  clearActivityImage(activityId: number): Observable<ActivityPromotion> {
    return this.apiService.delete<ActivityPromotion>(
      `/admin/activities/${activityId}/image`,
      this.apiService.createAuthHeaders()
    );
  }

  resolveImageUrl(imageUrl?: string | null): string {
    if (!imageUrl) {
      return '';
    }

    if (/^https?:\/\//i.test(imageUrl) || imageUrl.startsWith('data:')) {
      return imageUrl;
    }

    return `${this.assetBaseUrl}${imageUrl.startsWith('/') ? imageUrl : `/${imageUrl}`}`;
  }
}
