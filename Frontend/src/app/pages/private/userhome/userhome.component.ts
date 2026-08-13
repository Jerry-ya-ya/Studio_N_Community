import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Component, ChangeDetectionStrategy } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-userhome',
  standalone: false,
  templateUrl: './userhome.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './userhome.component.css'
})
export class UserhomeComponent {
  posts: any[] = [];
  users: any[] = [];
  
  loading = true;
  error = false;
  errorKey = '';
  errorParams: { status?: number; detail?: string } = {};

  public environment = environment;
  public apiRoot: string = environment.apiUrl.replace('/api', '');
  
  constructor(private route: ActivatedRoute, private http: HttpClient) {}
  
  get headers() {
    const token = localStorage.getItem('token');
    return new HttpHeaders({ Authorization: `Bearer ${token}` });
  }

  loadAllUsers() {
    console.log('Loading all users');
    
    this.http.get<any[]>(`${environment.apiUrl}/square`, { headers: this.headers })
      .subscribe({
        next: (usersData) => {
          console.log('Users data received:', usersData);
          this.users = usersData;
          this.loadAllPosts();
        },
        error: (err) => {
          console.error('Failed to load users:', err);
          this.error = true;
          this.errorKey = 'privateHome.error.loadUsers';
          this.errorParams = {
            status: err.status,
            detail: err.error?.error || err.message || ''
          };
          this.loading = false;
        }
      });
  }

  loadAllPosts() {
    console.log('Loading all posts');
    
    this.http.get<any[]>(`${environment.apiUrl}/post`, { headers: this.headers })
      .subscribe({
        next: (postsData) => {
          console.log('Posts data received:', postsData);
          this.posts = postsData;
          this.loading = false;
        },
        error: (err) => {
          console.error('Failed to load posts:', err);
          this.error = true;
          this.errorKey = 'privateHome.error.loadPosts';
          this.errorParams = {
            status: err.status,
            detail: err.error?.error || err.message || ''
          };
          this.loading = false;
        }
      });
  }

  // 根據用戶 ID 獲取用戶資料
  getUserById(userId: number): any {
    return this.users.find(user => user.id === userId);
  }

  getAvatarInitial(user: any) {
    return (user?.nickname || user?.username || '?').charAt(0).toUpperCase();
  }

  toggleLike(post: any) {
    if (post.likePending) {
      return;
    }

    post.likePending = true;
    this.http.post<{ liked_by_me: boolean; like_count: number }>(
      `${environment.apiUrl}/post/${post.id}/like`,
      {},
      { headers: this.headers }
    ).subscribe({
      next: response => {
        post.liked_by_me = response.liked_by_me;
        post.like_count = response.like_count;
        post.likePending = false;
      },
      error: err => {
        console.error('Failed to toggle post like:', err);
        post.likePending = false;
      }
    });
  }

  ngOnInit(): void {
    console.log('UserHome component initialized - loading all users and posts');
    this.loadAllUsers();
  }
}
