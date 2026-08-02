import { Injectable } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { ApiService } from './api.service';

export type MemberRole = 'superadmin' | 'admin' | 'member' | 'user';

export const memberRoleOptions: MemberRole[] = ['superadmin', 'admin', 'member', 'user'];

export interface MemberContentItem {
  id?: number | null;
  name: string;
  username?: string;
  role: MemberRole;
  githubUrl: string;
  avatarUrl?: string | null;
  avatarSource?: 'local' | 'github';
  sort_order?: number;
}

export const defaultMemberContent: MemberContentItem[] = Array.from({ length: 12 }, (_, index) => ({
  id: null,
  name: 'Jerry-ya-ya',
  role: 'member',
  githubUrl: 'https://github.com/Jerry-ya-ya',
  sort_order: index
}));

@Injectable({
  providedIn: 'root'
})
export class MemberContentService {
  private members = this.clone(defaultMemberContent);

  constructor(private apiService: ApiService) {}

  getSnapshot(): MemberContentItem[] {
    return this.clone(this.members);
  }

  loadPublicContent(): Observable<MemberContentItem[]> {
    return this.apiService.get<MemberContentItem[]>('/content/members').pipe(
      tap(members => this.members = this.normalizeMembers(members))
    );
  }

  loadAdminContent(): Observable<MemberContentItem[]> {
    return this.apiService.get<MemberContentItem[]>('/admin/content/members', this.apiService.createAuthHeaders()).pipe(
      tap(members => this.members = this.normalizeMembers(members))
    );
  }

  saveAdminContent(members: MemberContentItem[]): Observable<MemberContentItem[]> {
    return this.apiService.put<MemberContentItem[]>(
      '/admin/content/members',
      members,
      this.apiService.createAuthHeaders()
    ).pipe(
      tap(saved => this.members = this.normalizeMembers(saved))
    );
  }

  getDefaultContent(): MemberContentItem[] {
    return this.clone(defaultMemberContent);
  }

  normalizeMembers(items: unknown): MemberContentItem[] {
    if (!Array.isArray(items)) {
      return this.clone(defaultMemberContent);
    }

    const members = items.map((item, index) => {
      const member = item as Partial<MemberContentItem>;
      const avatarSource: 'local' | 'github' = member.avatarSource === 'local' ? 'local' : 'github';
      return {
        id: member.id ?? null,
        name: String(member.name ?? '').trim(),
        username: String(member.username ?? '').trim(),
        role: this.normalizeRole(member.role),
        githubUrl: String(member.githubUrl ?? '').trim(),
        avatarUrl: member.avatarUrl ? String(member.avatarUrl).trim() : null,
        avatarSource,
        sort_order: Number(member.sort_order ?? index)
      };
    }).filter(member => member.name || member.role || member.githubUrl);

    return members.length ? members : this.clone(defaultMemberContent);
  }

  private clone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
  }

  private normalizeRole(role: unknown): MemberRole {
    return memberRoleOptions.includes(role as MemberRole) ? role as MemberRole : 'member';
  }
}
