import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
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
  constructor(private http: HttpClient) {}
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
        error: err => this.message = '載入用戶失敗'
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
    const roleMap: { [key: string]: string } = {
      'user': '一般用戶',
      'admin': '管理員',
      'superadmin': '最高管理員'
    };
    return roleMap[role] || role;
  }

  getAccountStatus(user: User): string {
    return user.is_deleted ? '已刪除' : '啟用中';
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
    return date.toLocaleDateString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
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
          this.message = err.error.error || '晉升失敗';
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
          this.message = err.error.error || '降級失敗';
          this.demotingUserId = null;
          setTimeout(() => this.message = '', 3000);
        }
      });
  }
}
