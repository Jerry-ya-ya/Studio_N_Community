import { HttpClient } from '@angular/common/http';
import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { ApiService } from '../../../core/services/api.service';
import { environment } from '../../../../environments/environment';

interface GithubProfile {
  avatar_url: string;
  login: string;
}

interface FriendItem {
  id: number;
  username: string;
  name?: string | null;
  nickname?: string | null;
  email?: string | null;
  githubUrl?: string | null;
  avatarUrl?: string | null;
  avatarSource?: 'local' | 'github';
}

@Component({
  selector: 'app-friend',
  standalone: false,
  templateUrl: './friend.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './friend.component.css'
})
export class FriendComponent implements OnInit {
  friendUsername: string = '';
  message: string = '';
  friends: FriendItem[] = [];
  public apiRoot: string = environment.apiUrl.replace('/api', '');
  private avatarByUsername: Record<string, string> = {};
  private avatarRequests = new Set<string>();

  toUsername: string = '';
  requests: any[] = [];

  constructor(
    private apiService: ApiService,
    private http: HttpClient,
    private translate: TranslateService
  ) {}

  ngOnInit(): void {
    this.refreshFriendPage();
  }

  // followFriend() {
  //   if (!this.friendUsername.trim()) return;

  //   this.apiService.post<any>(
  //     '/friends/follow',
  //     { friend_username: this.friendUsername },
  //     this.apiService.createAuthHeaders()
  //   ).subscribe({
  //     next: res => {
  //       this.message = res.message;
  //       this.friendUsername = '';
  //       this.loadFriends();
  //     },
  //     error: err => {
  //       this.message = err.error?.error || '發生錯誤';
  //     }
  //   });
  // }

  removeFriend(friendId: number) {
    this.apiService.delete<any>(
      `/friends/remove/${friendId}`,
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: res => {
        this.message = res.message;
        this.loadFriends(); // 重新載入清單
      },
      error: err => {
        this.message = err.error?.error || this.translate.instant('privateFriend.feedback.removeFailure');
      }
    });
  }

  loadFriends() {
    this.apiService.get<FriendItem[]>(
      '/friends/list',
      this.apiService.createAuthHeaders()
    ).subscribe(friends => {
      this.friends = friends.map(friend => ({
        ...friend,
        avatarSource: friend.avatarSource === 'local' ? 'local' : 'github'
      }));
      this.loadFriendAvatars(this.friends);
    });
  }

  sendRequest() {
    this.apiService.post<any>(
      '/friends/request',
      { to_username: this.toUsername },
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: res => {
        this.message = res.message;
        this.toUsername = '';
      },
      error: err => {
        this.message = err.error?.error || this.translate.instant('privateFriend.feedback.sendFailure');
      }
    });
  }

  loadRequests() {
    this.apiService.get<any[]>(
      '/friends/requests',
      this.apiService.createAuthHeaders()
    ).subscribe(res => this.requests = res);
  }

  refreshFriendPage() {
    this.loadFriends();
    this.loadRequests();
  }

  acceptRequest(id: number) {
    this.apiService.post(
      `/friends/accept/${id}`,
      {},
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: res => {
        this.message = (res as any).message;
        this.refreshFriendPage();
      },
      error: err => {
        this.message = err.error?.error || this.translate.instant('privateFriend.feedback.acceptFailure');
      }
    });
  }

  rejectRequest(id: number) {
    this.apiService.post(
      `/friends/reject/${id}`,
      {},
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: res => {
        this.message = (res as any).message;
        this.loadRequests();
      },
      error: err => {
        this.message = err.error?.error || this.translate.instant('privateFriend.feedback.rejectFailure');
      }
    });
  }

  getFriendAvatar(friend: FriendItem) {
    const localAvatar = this.getLocalAvatarUrl(friend);
    if (this.shouldUseLocalAvatar(friend) && localAvatar) {
      return localAvatar;
    }

    const githubUsername = this.getGithubUsername(friend);
    return (githubUsername ? this.avatarByUsername[githubUsername] : '') || localAvatar || 'icons/cmenstudio.png';
  }

  private loadFriendAvatars(friends: FriendItem[]) {
    for (const friend of friends) {
      if (this.shouldUseLocalAvatar(friend)) {
        continue;
      }

      const githubUsername = this.getGithubUsername(friend);
      if (!githubUsername) {
        continue;
      }

      if (this.avatarByUsername[githubUsername] || this.avatarRequests.has(githubUsername)) {
        continue;
      }

      this.avatarRequests.add(githubUsername);
      this.http.get<GithubProfile>(`https://api.github.com/users/${githubUsername}`).subscribe({
        next: profile => {
          this.avatarByUsername[githubUsername] = profile.avatar_url;
          this.avatarRequests.delete(githubUsername);
        },
        error: () => {
          this.avatarRequests.delete(githubUsername);
        }
      });
    }
  }

  private getGithubUsername(friend: FriendItem) {
    const url = this.normalizeGithubUrl(friend.githubUrl || '');
    return url.replace(/^https:\/\/github\.com\//, '').split('/')[0];
  }

  private normalizeGithubUrl(url: string) {
    const trimmed = (url || '').trim();
    if (!trimmed) {
      return '';
    }

    if (/^https?:\/\//i.test(trimmed)) {
      return trimmed.replace(/^http:\/\//i, 'https://').replace(/\/+$/, '');
    }

    return `https://github.com/${trimmed.replace(/^@/, '').replace(/^github\.com\//i, '').replace(/\/+$/, '')}`;
  }

  private getLocalAvatarUrl(friend: FriendItem) {
    if (!friend.avatarUrl) {
      return '';
    }

    return /^https?:\/\//i.test(friend.avatarUrl) ? friend.avatarUrl : `${this.apiRoot}/${friend.avatarUrl}`;
  }

  private shouldUseLocalAvatar(friend: FriendItem) {
    return friend.avatarSource === 'local';
  }
}
