import { Component, OnInit, ChangeDetectionStrategy, HostListener } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';
import { ApiService } from '../../../core/services/api.service';
import { toRomanNumeral } from '../../../shared/project-level';

interface ProjectRecruitmentUser {
  id: number;
  username: string;
  nickname?: string;
  avatar_url?: string;
  role?: string;
}

interface ProjectRecruitmentMember {
  id: number;
  message?: string;
  created_at?: string;
  user: ProjectRecruitmentUser;
}

interface ProjectRecruitment {
  id: number;
  title: string;
  summary: string;
  role_needed?: string;
  contact?: string;
  github_url?: string;
  max_members?: number;
  review_status: 'open' | 'pending' | 'approved' | 'rejected';
  created_at?: string;
  creator: ProjectRecruitmentUser;
  members: ProjectRecruitmentMember[];
  member_count: number;
  level?: number;
  joined_by_me: boolean;
  owned_by_me: boolean;
}

@Component({
  selector: 'app-project-recruitment',
  standalone: false,
  templateUrl: './project-recruitment.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './project-recruitment.component.css'
})
export class ProjectRecruitmentComponent implements OnInit {
  readonly contactMethods = ['discord', 'email', 'site_message'];
  projects: ProjectRecruitment[] = [];
  loading = false;
  submitting = false;
  deletingProject: Record<number, boolean> = {};
  actionLoading: Record<number, boolean> = {};
  joinMessages: Record<number, string> = {};
  statusMessage = '';
  joinMessage = '';
  selectedProject: ProjectRecruitment | null = null;

  form = {
    title: '',
    summary: '',
    role_needed: '',
    contact: '',
    github_url: '',
    max_members: null as number | null,
  };

  constructor(
    private apiService: ApiService,
    private translate: TranslateService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.loadProjects();
  }

  loadProjects() {
    this.loading = true;
    this.apiService.get<ProjectRecruitment[]>('/project-recruitments', this.apiService.createAuthHeaders())
      .subscribe({
        next: projects => {
          this.projects = projects;
          this.loading = false;
        },
        error: err => {
          this.statusMessage = err.error?.error || this.translate.instant('privateRecruit.feedback.loadFailure');
          this.loading = false;
        }
      });
  }

  createProject() {
    if (this.submitting) {
      return;
    }

    if (!this.form.github_url.trim()) {
      this.openGithubUrlSnack('privateRecruit.feedback.githubUrlRequired');
      return;
    }

    if (!this.isValidGithubRepositoryUrl(this.form.github_url)) {
      this.openGithubUrlSnack('privateRecruit.feedback.githubUrlInvalid');
      return;
    }

    if (!this.form.title.trim() || !this.form.summary.trim()) {
      return;
    }

    this.submitting = true;
    this.apiService.post<ProjectRecruitment>(
      '/project-recruitments',
      this.form,
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: project => {
        this.projects = [project, ...this.projects];
        this.form = {
          title: '',
          summary: '',
          role_needed: '',
          contact: '',
          github_url: '',
          max_members: null,
        };
        this.statusMessage = this.translate.instant('privateRecruit.feedback.createSuccess');
        this.submitting = false;
      },
      error: err => {
        this.statusMessage = err.error?.error || this.translate.instant('privateRecruit.feedback.createFailure');
        this.submitting = false;
      }
    });
  }

  joinProject(project: ProjectRecruitment) {
    if (project.owned_by_me || project.joined_by_me || this.actionLoading[project.id]) {
      return;
    }

    this.actionLoading[project.id] = true;
    this.apiService.post<ProjectRecruitment>(
      `/project-recruitments/${project.id}/join`,
      { message: this.joinMessages[project.id] || '' },
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: updated => {
        this.replaceProject(updated);
        this.joinMessages[project.id] = '';
        this.actionLoading[project.id] = false;
      },
      error: err => {
        this.statusMessage = err.error?.error || this.translate.instant('privateRecruit.feedback.joinFailure');
        this.actionLoading[project.id] = false;
      }
    });
  }

  leaveProject(project: ProjectRecruitment) {
    if (!project.joined_by_me || this.actionLoading[project.id]) {
      return;
    }

    this.actionLoading[project.id] = true;
    this.apiService.delete<ProjectRecruitment>(
      `/project-recruitments/${project.id}/join`,
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: updated => {
        this.replaceProject(updated);
        this.actionLoading[project.id] = false;
      },
      error: err => {
        this.statusMessage = err.error?.error || this.translate.instant('privateRecruit.feedback.leaveFailure');
        this.actionLoading[project.id] = false;
      }
    });
  }

  deleteProject(project: ProjectRecruitment) {
    if (!project.owned_by_me || this.deletingProject[project.id]) {
      return;
    }

    this.deletingProject[project.id] = true;
    this.apiService.delete<{ message: string; id: number }>(
      `/project-recruitments/${project.id}`,
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: result => {
        this.projects = this.projects.filter(item => item.id !== result.id);
        delete this.deletingProject[project.id];
        this.statusMessage = this.translate.instant('privateRecruit.feedback.deleteSuccess');
      },
      error: err => {
        this.statusMessage = err.error?.error || this.translate.instant('privateRecruit.feedback.deleteFailure');
        delete this.deletingProject[project.id];
      }
    });
  }

  isFull(project: ProjectRecruitment) {
    return !!project.max_members && project.member_count >= project.max_members;
  }

  openProject(project: ProjectRecruitment) {
    this.selectedProject = project;
  }

  closeProject() {
    this.selectedProject = null;
  }

  @HostListener('document:keydown.escape')
  closeProjectOnEscape() {
    this.closeProject();
  }

  getDisplayName(user: ProjectRecruitmentUser) {
    return user.nickname || user.username;
  }

  getAvatarInitial(user: ProjectRecruitmentUser) {
    return this.getDisplayName(user).trim().charAt(0).toUpperCase() || '?';
  }

  getProjectLevel(project: ProjectRecruitment) {
    return toRomanNumeral(project.level);
  }

  getContactLabel(contact?: string) {
    return contact && this.contactMethods.includes(contact)
      ? this.translate.instant(`privateRecruit.contactMethods.${contact}`)
      : contact;
  }

  get ownedProjects() {
    return this.projects.filter(project => project.owned_by_me);
  }

  private replaceProject(updated: ProjectRecruitment) {
    this.projects = this.projects.map(project => project.id === updated.id ? updated : project);
    if (this.selectedProject?.id === updated.id) {
      this.selectedProject = updated;
    }
  }

  private isValidGithubRepositoryUrl(value: string) {
    try {
      const url = new URL(value.trim());
      const pathParts = url.pathname.split('/').filter(Boolean);
      return url.protocol === 'https:'
        && ['github.com', 'www.github.com'].includes(url.hostname)
        && pathParts.length === 2;
    } catch {
      return false;
    }
  }

  private openGithubUrlSnack(messageKey: string) {
    this.snackBar.open(
      this.translate.instant(messageKey),
      this.translate.instant('privateRecruit.actions.dismiss'),
      {
        duration: 5000,
        horizontalPosition: 'end',
        verticalPosition: 'top',
        panelClass: ['studio-snackbar', 'studio-snackbar-error']
      }
    );
  }
}
