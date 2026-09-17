import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';

import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { TranslateService } from '@ngx-translate/core';
import { AuthSessionService } from '../../../core/services/auth-session.service';
import { resolveImageUrl } from '../../../shared/image-url';

@Component({
  selector: 'app-profile',
  standalone: false,
  templateUrl: './profile.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './profile.component.css'
})
export class ProfileComponent implements OnInit {
  readonly experiencePerLevel = 100;
  readonly capabilityFields = [
    {
      key: 'capabilityDirection',
      labelKey: 'privateProfile.capabilities.fields.direction',
      options: ['cmenstudio', 'eden', 'both', 'independent']
    },
    {
      key: 'capabilityStack',
      labelKey: 'privateProfile.capabilities.fields.stack',
      options: ['frontend', 'backend', 'fullstack', 'creative']
    },
    {
      key: 'capabilityFocus',
      labelKey: 'privateProfile.capabilities.fields.focus',
      options: ['game-systems', 'learning-networks', 'community', 'developer-tools']
    },
    {
      key: 'capabilityStyle',
      labelKey: 'privateProfile.capabilities.fields.style',
      options: ['professional', 'game-driven', 'experimental', 'collaborative']
    }
  ] as const;

  // email, nickname
  user: any = null;
  editing = false;
  success = '';
  mode = 'login'; // 預設為登入
  public environment = environment;
  public apiRoot: string = environment.apiUrl.replace('/api', '');

  constructor(
    private http: HttpClient,
    private translate: TranslateService,
    private authSession: AuthSessionService
  ) {}
  isLoggedIn() {
    return this.authSession.isAuthenticated;
  }

  getImageUrl(imageUrl?: string | null) {
    return resolveImageUrl(imageUrl, this.apiRoot);
  }

  logout() {
    this.http.delete(`${environment.apiUrl}/refresh`).subscribe({ error: () => undefined });
    this.authSession.clear();
    location.reload();  // 或導向登入頁
  }

  experienceProgress(experience: unknown): number {
    return this.normalizeExperience(experience) % this.experiencePerLevel;
  }

  experienceRemaining(experience: unknown): number {
    return this.experiencePerLevel - this.experienceProgress(experience);
  }

  ngOnInit() {
    // The first request after a reload can restore the in-memory access token
    // through the HttpOnly refresh cookie in AuthInterceptor.
    this.http.get<any>(`${environment.apiUrl}/me`).subscribe({
        next: (data) => {
          this.user = {
            ...data,
            avatarSource: data.avatarSource || data.avatar_source || 'github',
            ...this.normalizeCapabilities(data)
          };
          console.log('Loaded user successfully', this.user);
        },
        error: (err) => console.error('Failed to get user data:', err)
    });
  }

  loadProfile() {
    this.http.get<any>(`${environment.apiUrl}/me`).subscribe({
      next: data => {
        this.user = {
          ...data,
          avatarSource: data.avatarSource || data.avatar_source || 'github',
          ...this.normalizeCapabilities(data)
        };
      },
      error: () => alert(this.translate.instant('privateProfile.feedback.loadFailure'))
    });
  }

  saveProfile() {
    this.updateProfile({
      email: this.user.email,
      nickname: this.user.nickname,
      githubUrl: this.user.githubUrl || this.user.github_url || '',
      avatarSource: this.user.avatarSource || this.user.avatar_source || 'github',
      ...this.capabilityPayload()
    }).subscribe({
      next: () => {
        this.success = this.translate.instant('privateProfile.feedback.updateSuccess');
        this.editing = false;
      },
      error: () => alert(this.translate.instant('privateProfile.feedback.updateFailure'))
    });
  }

  saveAvatarSource(showSuccess = true) {
    this.updateProfile({
      email: this.user.email,
      nickname: this.user.nickname,
      githubUrl: this.user.githubUrl || this.user.github_url || '',
      avatarSource: this.user.avatarSource || this.user.avatar_source || 'github'
    }).subscribe({
      next: () => {
        if (showSuccess) {
          this.success = this.translate.instant('privateProfile.feedback.avatarSourceSuccess');
        }
      },
      error: () => alert(this.translate.instant('privateProfile.feedback.updateFailure'))
    });
  }

  // 上傳頭像
  avatarPreview: string | null = null;
  selectedFile: File | null = null;

  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file) {
      this.selectedFile = file;
      const reader = new FileReader();
      reader.onload = e => this.avatarPreview = reader.result as string;
      reader.readAsDataURL(file);
    }
  }

  uploadAvatar() {
    if (!this.selectedFile) return;

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.http.post<any>(`${environment.apiUrl}/avatar`, formData).subscribe({
      next: res => {
        this.user.avatar_url = res.avatar_url;
        this.user.avatarSource = 'local';
        this.user.avatar_source = 'local';
        this.avatarPreview = null;
        this.saveAvatarSource(false);
        alert(this.translate.instant('privateProfile.feedback.avatarSuccess'));
      },
      error: () => alert(this.translate.instant('privateProfile.feedback.avatarFailure'))
    });
  }

  private updateProfile(payload: Record<string, unknown>) {
    return this.http.put(`${environment.apiUrl}/me`, payload);
  }

  private capabilityPayload() {
    return Object.fromEntries(
      this.capabilityFields.map(field => [field.key, this.user[field.key]])
    );
  }

  private normalizeCapabilities(data: any) {
    const defaults: Record<string, string> = {
      capabilityDirection: 'both',
      capabilityStack: 'fullstack',
      capabilityFocus: 'game-systems',
      capabilityStyle: 'professional'
    };

    return Object.fromEntries(this.capabilityFields.map(field => {
      const snakeKey = field.key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
      const value = data[field.key] || data[snakeKey];
      return [field.key, (field.options as readonly unknown[]).includes(value) ? value : defaults[field.key]];
    }));
  }

  private normalizeExperience(experience: unknown): number {
    const value = Number(experience ?? 0);
    return Number.isFinite(value) ? Math.max(0, Math.floor(value)) : 0;
  }
}
