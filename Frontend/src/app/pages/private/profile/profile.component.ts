import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';

import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';
import { HttpHeaders } from '@angular/common/http';
import { TranslateService } from '@ngx-translate/core';

@Component({
  selector: 'app-profile',
  standalone: false,
  templateUrl: './profile.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './profile.component.css'
})
export class ProfileComponent implements OnInit {
  // email, nickname
  user: any = null;
  editing = false;
  success = '';
  mode = 'login'; // 預設為登入
  public environment = environment;
  public apiRoot: string = environment.apiUrl.replace('/api', '');

  constructor(
    private http: HttpClient,
    private translate: TranslateService
  ) {}
  isLoggedIn() {
    const token = localStorage.getItem('token');
    return !!localStorage.getItem('token');
  }

  logout() {
    localStorage.removeItem('token');
    location.reload();  // 或導向登入頁
  }

  ngOnInit() {
    if (this.isLoggedIn()) {
      const token = localStorage.getItem('token');
      const headers = new HttpHeaders({Authorization: `Bearer ${token}`});
      // 取得使用者資料
      this.http.get<any>(`${environment.apiUrl}/me`, { headers }).subscribe({
        next: (data) => {
          this.user = {
            ...data,
            avatarSource: data.avatarSource || data.avatar_source || 'github'
          };
          console.log('Loaded user successfully', this.user);
        },
        error: (err) => {
          if (err.status === 401) {
            // Token 無效才登出
            this.logout();
          } else {
            // 其他錯誤：只記錄錯誤，不登出
            console.error('Failed to get user data:', err);
          }
        }
      });
    }
  }

  loadProfile() {
    this.http.get<any>(`${environment.apiUrl}/me`).subscribe({
      next: data => {
        this.user = {
          ...data,
          avatarSource: data.avatarSource || data.avatar_source || 'github'
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
      avatarSource: this.user.avatarSource || this.user.avatar_source || 'github'
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
    const token = localStorage.getItem('token');
    const headers = new HttpHeaders({Authorization: `Bearer ${token}`});

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.http.post<any>(`${environment.apiUrl}/avatar`, formData, { headers }).subscribe({
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
}
