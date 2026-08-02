import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';

interface ProjectUser {
  id: number;
  username: string;
  nickname?: string | null;
  avatar_url?: string | null;
  role?: string;
}

interface ProjectMember {
  id: number;
  message?: string | null;
  created_at: string;
  user: ProjectUser;
}

interface ProjectTodo {
  id: number;
  text: string;
  done: boolean;
  priority: number;
  user_id?: number | null;
  created_by_id?: number | null;
  claimed_by_id?: number | null;
  assignee_name?: string | null;
  claimed_by_name?: string | null;
  created_at: string;
}

interface AdminProject {
  id: number;
  title: string;
  summary: string;
  role_needed?: string | null;
  contact?: string | null;
  max_members?: number | null;
  created_at: string;
  creator: ProjectUser;
  members: ProjectMember[];
  todos: ProjectTodo[];
  member_count: number;
}

@Component({
  selector: 'app-projects',
  standalone: false,
  templateUrl: './projects.component.html',
  styleUrl: './projects.component.css',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class ProjectsComponent implements OnInit {
  projects: AdminProject[] = [];
  expandedTodoProjectIds = new Set<number>();
  loading = false;
  errorMessage = '';

  constructor(
    private apiService: ApiService,
    private changeDetectorRef: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadProjects();
  }

  loadProjects() {
    this.loading = true;
    this.errorMessage = '';

    this.apiService.get<AdminProject[]>('/admin/project-recruitments', this.apiService.createAuthHeaders())
      .subscribe({
        next: projects => {
          this.projects = projects;
          this.loading = false;
          this.changeDetectorRef.detectChanges();
        },
        error: error => {
          this.errorMessage = error?.error?.error || 'adminProjects.feedback.loadFailure';
          this.loading = false;
          this.changeDetectorRef.detectChanges();
        }
      });
  }

  getDisplayName(user?: ProjectUser | null) {
    if (!user) {
      return '-';
    }
    return user.nickname || user.username || '-';
  }

  toggleTodos(projectId: number) {
    if (this.expandedTodoProjectIds.has(projectId)) {
      this.expandedTodoProjectIds.delete(projectId);
    } else {
      this.expandedTodoProjectIds.add(projectId);
    }
  }

  isTodosExpanded(projectId: number) {
    return this.expandedTodoProjectIds.has(projectId);
  }

  getActiveTodos(project: AdminProject) {
    return (project.todos || []).filter(todo => !todo.done);
  }

  getDoneTodos(project: AdminProject) {
    return (project.todos || []).filter(todo => todo.done);
  }

}
