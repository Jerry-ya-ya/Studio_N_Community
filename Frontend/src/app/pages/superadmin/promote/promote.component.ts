import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { environment } from '../../../../environments/environment';

interface User {
  id: number;
  username: string;
  email: string;
  nickname?: string;
  role: string;
  email_verified: boolean;
  is_deleted?: boolean;
  avatar_url?: string;
  avatarUrl?: string;
  avatar_source?: string;
  avatarSource?: string;
  created_at: string;
  experience?: number;
  coins?: number;
  total_coins?: number;
  totalCoins?: number;
  total_points?: number;
  totalPoints?: number;
  imageLoadFailed?: boolean;
}

@Component({
  selector: 'app-promote',
  standalone: false,
  templateUrl: './promote.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './promote.component.css'
})
export class PromoteComponent implements OnInit {
  users: User[] = [];
  filteredUsers: User[] = [];
  message = '';
  searchTerm = '';
  promotingUserId: number | null = null;
  demotingUserId: number | null = null;
  constructor(
    private http: HttpClient,
    private translate: TranslateService
  ) {}
  public apiRoot: string = environment.apiUrl.replace('/api', '');

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers() {
    const token = localStorage.getItem('token');
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    this.http.get<User[]>(`${environment.apiUrl}/superadmin/promote`, { headers })
      .subscribe({
      next: users => {
        this.users = users;
        this.filterUsers();
      },
      error: err => this.message = this.translate.instant('superadminPromote.feedback.loadFailed')
    });
  }

  filterUsers() {
    if (!this.searchTerm.trim()) {
      this.filteredUsers = this.users;
    } else {
      const term = this.searchTerm.toLowerCase();
      this.filteredUsers = this.users.filter(user =>
        user.username.toLowerCase().includes(term) ||
        user.email.toLowerCase().includes(term) ||
        (user.nickname && user.nickname.toLowerCase().includes(term))
      );
    }
  }

  getUsersByRole(role: string): User[] {
    return this.users.filter(user => user.role === role);
  }

  getRoleDisplayName(role: string): string {
    return this.translate.instant(`superadminPromote.roles.${role}`) || role;
  }

  getAccountStatus(user: User): string {
    const statusKey = user.is_deleted ? 'deleted' : 'active';
    return this.translate.instant(`superadminPromote.accountStatus.${statusKey}`);
  }

  getUserCoins(user: User): number {
    return user.totalCoins ?? user.total_coins ?? user.coins ?? user.totalPoints ?? user.total_points ?? 0;
  }

  getUserAvatar(user: User): string {
    const avatarUrl = user.avatarUrl || user.avatar_url || '';

    if (!avatarUrl || user.imageLoadFailed) {
      return '';
    }

    if (/^https?:\/\//i.test(avatarUrl)) {
      return avatarUrl;
    }

    return `${this.apiRoot}/${avatarUrl.replace(/^\/+/, '')}`;
  }

  getUserInitial(user: User): string {
    const label = (user.nickname || user.username || user.email || '?').trim();
    return label.charAt(0).toUpperCase() || '?';
  }

  markAvatarFailed(user: User): void {
    user.imageLoadFailed = true;
  }

  formatDate(dateString: string): string {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString(this.getDateLocale(), {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  private getDateLocale(): string {
    const localeMap: { [key: string]: string } = {
      en: 'en-US',
      'zh-TW': 'zh-TW',
      ja: 'ja-JP',
      ko: 'ko-KR'
    };
    const language = localStorage.getItem('language') || 'en';
    return localeMap[language] || 'en-US';
  }

  promote(userId: number) {
    this.promotingUserId = userId;
    const token = localStorage.getItem('token');
    const headers = new HttpHeaders().set('Authorization', `Bearer ${token}`);
    
    this.http.put<any>(`${environment.apiUrl}/superadmin/promote/${userId}`, {}, { headers })
      .subscribe({
        next: res => {
          this.message = res.message;
          this.loadUsers();
          this.promotingUserId = null;
          
          // 3秒後清除訊息
          setTimeout(() => {
            this.message = '';
          }, 3000);
        },
        error: err => {
          this.message = err.error.error || this.translate.instant('superadminPromote.feedback.promoteFailed');
          this.promotingUserId = null;
          
          // 3秒後清除錯誤訊息
          setTimeout(() => {
            this.message = '';
          }, 3000);
        }
      });
  }

  demote(userId: number) {
    this.demotingUserId = userId;
    const token = localStorage.getItem('token');
    const headers = { Authorization: `Bearer ${token}` };
    this.http.put<any>(`${environment.apiUrl}/superadmin/demote/${userId}`, {}, { headers })
      .subscribe({
        next: res => {
          this.message = res.message;
          this.loadUsers();
          this.demotingUserId = null;
          setTimeout(() => this.message = '', 3000);
        },
        error: err => {
          this.message = err.error.error || this.translate.instant('superadminPromote.feedback.demoteFailed');
          this.demotingUserId = null;
          setTimeout(() => this.message = '', 3000);
        }
      });
  }
}
