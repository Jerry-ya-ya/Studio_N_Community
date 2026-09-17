import { Component, ChangeDetectionStrategy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { TranslateService } from '@ngx-translate/core';
import { environment } from '../../../../environments/environment';
import { resolveImageUrl } from '../../../shared/image-url';

@Component({
  selector: 'app-post',
  standalone: false,
  templateUrl: './post.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './post.component.css'
})
export class PostComponent {
  // 貼文內容
  content: string = '';
  // 貼文列表
  posts: any[] = [];
  // 使用者資料
  user: any = null;
  // 訊息
  message = '';
  // 編輯模式
  editMode: { [key: number]: boolean } = {};
  editContent: { [key: number]: string } = {};
  // 環境變數
  public environment = environment;
  public apiRoot: string = environment.apiUrl.replace('/api', '');

  constructor(
    private http: HttpClient,
    private translate: TranslateService
  ) {}

  ngOnInit(): void {
    this.loadMyPosts();
    this.loadProfile();
  }

  loadProfile() {
    this.http.get<any>(`${environment.apiUrl}/me`).subscribe({
      next: data => {
        this.user = data;
      },
      error: () => alert(this.translate.instant('postWall.feedback.profileFailure'))
    });
  }

  loadMyPosts() {
    this.http.get<any[]>(`${environment.apiUrl}/post/me`)
      .subscribe(data => this.posts = data);
  }

  getAvatarInitial(user: any) {
    return (user?.nickname || user?.username || '?').charAt(0).toUpperCase();
  }

  getImageUrl(imageUrl?: string | null) {
    return resolveImageUrl(imageUrl, this.apiRoot);
  }

  submitPost() {
    this.http.post<any>(`${environment.apiUrl}/post`, { content: this.content })
      .subscribe({
        next: res => {
          this.message = res.message;
          this.content = '';
          this.loadMyPosts();
        },
        error: err => {
          this.message = err.error?.error || 'postWall.feedback.createFailure';
        }
      });
  }

  enableEdit(post: any) {
    this.editMode[post.id] = true;
    this.editContent[post.id] = post.content;
  }
  
  cancelEdit(postId: number) {
    this.editMode[postId] = false;
  }
  
  updatePost(postId: number) {
    const newContent = this.editContent[postId];
    this.http.put(`${environment.apiUrl}/post/${postId}`, { content: newContent })
      .subscribe({
        next: res => {
          this.message = (res as any).message;
          this.editMode[postId] = false;
          this.loadMyPosts();
        },
        error: err => {
          this.message = err.error?.error || 'postWall.feedback.updateFailure';
        }
      });
  }
  
  deletePost(postId: number) {
    if (!confirm(this.translate.instant('postWall.confirm.delete'))) return;
  
    this.http.delete(`${environment.apiUrl}/post/${postId}`)
      .subscribe({
        next: res => {
          this.message = (res as any).message;
          this.loadMyPosts();
        },
        error: err => {
          this.message = err.error?.error || 'postWall.feedback.deleteFailure';
        }
      });
  }
}
