import { HttpClient } from '@angular/common/http';
import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { forkJoin } from 'rxjs';
import { defaultMemberContent, MemberContentItem, MemberContentService } from '../../../core/services/member-content.service';
import { environment } from '../../../../environments/environment';

interface GithubProfile {
  avatar_url: string;
  bio: string | null;
  blog: string | null;
  company: string | null;
  followers: number;
  following: number;
  html_url: string;
  location: string | null;
  login: string;
  name: string | null;
  public_repos: number;
}

interface GithubRepository {
  description: string | null;
  fork: boolean;
  html_url: string;
  language: string | null;
  name: string;
  stargazers_count: number;
  updated_at: string;
}

interface MemberCapability {
  labelKey: string;
  valueKey: string;
}

@Component({
  selector: 'app-member',
  standalone: false,
  templateUrl: './member.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './member.component.css'
})
export class MemberComponent implements OnInit {
  demoMembers: MemberContentItem[] = JSON.parse(JSON.stringify(defaultMemberContent));

  readonly capabilities: MemberCapability[] = [
    { labelKey: 'member.capabilities.direction.label', valueKey: 'member.capabilities.direction.value' },
    { labelKey: 'member.capabilities.stack.label', valueKey: 'member.capabilities.stack.value' },
    { labelKey: 'member.capabilities.focus.label', valueKey: 'member.capabilities.focus.value' },
    { labelKey: 'member.capabilities.style.label', valueKey: 'member.capabilities.style.value' }
  ];

  selectedMember: MemberContentItem = this.demoMembers[0];
  profile: GithubProfile | null = null;
  repositories: GithubRepository[] = [];
  loading = true;
  error = '';
  public apiRoot = environment.apiUrl.replace('/api', '');
  private avatarByUsername: Record<string, string> = {};
  private avatarRequests = new Set<string>();

  constructor(
    private http: HttpClient,
    private memberContent: MemberContentService,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {
    this.memberContent.loadPublicContent().subscribe({
      next: members => {
        this.demoMembers = members;
        this.selectedMember = this.getInitialMember(members);
        this.loadMemberAvatars(this.demoMembers);
        this.loadGithubProfile(this.selectedMember);
      },
      error: () => {
        this.demoMembers = this.memberContent.getDefaultContent();
        this.selectedMember = this.getInitialMember(this.demoMembers);
        this.loadMemberAvatars(this.demoMembers);
        this.loadGithubProfile(this.selectedMember);
      }
    });
  }

  selectMember(member: MemberContentItem) {
    if (this.selectedMember === member && this.profile) {
      return;
    }

    this.selectedMember = member;
    this.loadGithubProfile(member);
  }

  loadGithubProfile(member = this.selectedMember) {
    this.loading = true;
    this.error = '';
    const githubUsername = this.getGithubUsername(member);

    if (!githubUsername) {
      this.profile = this.getFallbackProfile(member);
      this.repositories = [];
      this.loading = false;
      this.scrollToRequestedFragment();
      return;
    }

    forkJoin({
      profile: this.http.get<GithubProfile>(`https://api.github.com/users/${githubUsername}`),
      repositories: this.http.get<GithubRepository[]>(
        `https://api.github.com/users/${githubUsername}/repos?sort=updated&per_page=8`
      )
    }).subscribe({
      next: ({ profile, repositories }) => {
        this.profile = profile;
        this.avatarByUsername[profile.login] = profile.avatar_url;
        this.repositories = repositories.filter(repo => !repo.fork).slice(0, 6);
        this.loading = false;
        this.scrollToRequestedFragment();
      },
      error: () => {
        this.profile = this.getFallbackProfile(member);
        this.repositories = [];
        this.error = 'member.state.githubUnavailable';
        this.loading = false;
        this.scrollToRequestedFragment();
      }
    });
  }

  get displayName() {
    return this.profile?.name || this.selectedMember.name;
  }

  get profileBio() {
    return this.profile?.bio || '';
  }

  get profileBlog() {
    if (!this.profile?.blog) {
      return '';
    }

    return this.profile.blog.startsWith('http') ? this.profile.blog : `https://${this.profile.blog}`;
  }

  get profileUrl() {
    return this.normalizeGithubUrl(this.selectedMember.githubUrl);
  }

  get hasGithubProfile() {
    return !!this.profileUrl;
  }

  get displayGithubUsername() {
    return this.getGithubUsername(this.selectedMember) || this.selectedMember.username || this.selectedMember.name;
  }

  get memberAvatar() {
    const localAvatar = this.getLocalAvatarUrl(this.selectedMember);
    if (this.shouldUseLocalAvatar(this.selectedMember) && localAvatar) {
      return localAvatar;
    }

    const githubUsername = this.getGithubUsername(this.selectedMember);
    return this.profile?.avatar_url || (githubUsername ? this.avatarByUsername[githubUsername] : '') || localAvatar || 'icons/cmenstudio.png';
  }

  getMemberAvatar(member: MemberContentItem) {
    const localAvatar = this.getLocalAvatarUrl(member);
    if (this.shouldUseLocalAvatar(member) && localAvatar) {
      return localAvatar;
    }

    const githubUsername = this.getGithubUsername(member);
    return (githubUsername ? this.avatarByUsername[githubUsername] : '') || localAvatar || 'icons/cmenstudio.png';
  }

  private loadMemberAvatars(members: MemberContentItem[]) {
    for (const member of members) {
      if (this.shouldUseLocalAvatar(member)) {
        continue;
      }

      const githubUsername = this.getGithubUsername(member);
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

  private getInitialMember(members: MemberContentItem[]) {
    const requestedUsername = (this.route.snapshot.queryParamMap.get('username') || '').toLowerCase();
    const requestedId = Number(this.route.snapshot.queryParamMap.get('id') || 0);

    return members.find(member =>
      (requestedUsername && String(member.username || '').toLowerCase() === requestedUsername) ||
      (requestedUsername && this.getGithubUsername(member).toLowerCase() === requestedUsername) ||
      (requestedId && member.id === requestedId)
    ) || members[0] || this.memberContent.getDefaultContent()[0];
  }

  private scrollToRequestedFragment() {
    const fragment = this.route.snapshot.fragment;
    if (!fragment) {
      return;
    }

    setTimeout(() => {
      document.getElementById(fragment)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 0);
  }

  private getFallbackProfile(member: MemberContentItem): GithubProfile {
    const githubUsername = this.getGithubUsername(member);

    return {
      avatar_url: 'icons/cmenstudio.png',
      bio: null,
      blog: null,
      company: 'CMENStudio',
      followers: 0,
      following: 0,
      html_url: this.normalizeGithubUrl(member.githubUrl),
      location: null,
      login: githubUsername || member.username || member.name,
      name: member.name,
      public_repos: 0
    };
  }

  private getGithubUsername(member: MemberContentItem) {
    const url = this.normalizeGithubUrl(member.githubUrl);
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

  private getLocalAvatarUrl(member: MemberContentItem) {
    if (!member.avatarUrl) {
      return '';
    }

    return /^https?:\/\//i.test(member.avatarUrl) ? member.avatarUrl : `${this.apiRoot}/${member.avatarUrl}`;
  }

  private shouldUseLocalAvatar(member: MemberContentItem) {
    return member.avatarSource === 'local';
  }
}
