import { Component, ChangeDetectionStrategy } from '@angular/core';

import { OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-square',
  standalone: false,
  templateUrl: './square.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './square.component.css'
})
export class SquareComponent implements OnInit {
  users: any[] = [];
  user: any;
  userId!: number;
  currentUserId: number | null = null;
  friendIds = new Set<number>();
  friendMessages: Record<number, string> = {};
  friendActionLoading: Record<number, boolean> = {};
  
  public environment = environment;
  public apiRoot: string = environment.apiUrl.replace('/api', '');

  constructor(
    private route: ActivatedRoute,
    private http: HttpClient,
    private translate: TranslateService
  ) {}
  
  ngOnInit(): void {
    this.userId = Number(this.route.snapshot.paramMap.get('id'));

    // 取得使用者資料
    this.http.get<any[]>(`${environment.apiUrl}/square`).subscribe({
      next: data => {
        this.users = data;
        console.log('Loaded square users', this.users);
      },
      error: () => alert(this.translate.instant('privateSquare.feedback.loadUsersFailure'))
    });

    this.loadFriends();
    this.loadCurrentUser();
  }

  loadCurrentUser() {
    this.http.get<any>(`${environment.apiUrl}/me`).subscribe({
      next: user => {
        this.currentUserId = user.id;
      },
      error: () => {
        console.error('Failed to load current user');
      }
    });
  }

  loadFriends() {
    this.http.get<any[]>(`${environment.apiUrl}/friends/list`).subscribe({
      next: friends => {
        this.friendIds = new Set(friends.map(friend => friend.id));
      },
      error: () => {
        console.error('Failed to load friend list');
      }
    });
  }

  isFriend(userId: number) {
    return this.friendIds.has(userId);
  }

  isCurrentUser(userId: number) {
    return this.currentUserId === userId;
  }

  getAvatarInitial(user: any) {
    return (user?.nickname || user?.username || '?').charAt(0).toUpperCase();
  }

  sendFriendRequest(user: any) {
    if (!user?.username || this.isCurrentUser(user.id) || this.friendActionLoading[user.id]) {
      return;
    }

    this.friendActionLoading[user.id] = true;
    this.http.post<any>(
      `${environment.apiUrl}/friends/request`,
      { to_username: user.username }
    ).subscribe({
      next: res => {
        this.friendMessages[user.id] = res.message || this.translate.instant('privateSquare.feedback.inviteSent');
        this.friendActionLoading[user.id] = false;
      },
      error: err => {
        this.friendMessages[user.id] = err.error?.error || this.translate.instant('privateSquare.feedback.inviteFailure');
        this.friendActionLoading[user.id] = false;
      }
    });
  }

  removeFriend(user: any) {
    if (!user?.id || this.isCurrentUser(user.id) || this.friendActionLoading[user.id]) {
      return;
    }

    this.friendActionLoading[user.id] = true;
    this.http.delete<any>(
      `${environment.apiUrl}/friends/remove/${user.id}`
    ).subscribe({
      next: res => {
        this.friendIds.delete(user.id);
        this.friendMessages[user.id] = res.message || this.translate.instant('privateSquare.feedback.removeSuccess');
        this.friendActionLoading[user.id] = false;
      },
      error: err => {
        this.friendMessages[user.id] = err.error?.error || this.translate.instant('privateSquare.feedback.removeFailure');
        this.friendActionLoading[user.id] = false;
      }
    });
  }
}
