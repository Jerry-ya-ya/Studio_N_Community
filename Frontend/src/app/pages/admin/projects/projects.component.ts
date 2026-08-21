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
  settled: boolean;
  priority: number;
  difficulty: number;
  duration: number;
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
  token_budget?: number;
  tokenBudget?: number;
  token_used?: number;
  tokenUsed?: number;
  token_remaining?: number;
  tokenRemaining?: number;
  review_status: 'open' | 'pending' | 'approved' | 'rejected';
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
  readonly difficultyOptions = [2, 4, 6, 9, 13];
  projects: AdminProject[] = [];
  expandedTodoProjectIds = new Set<number>();
  reviewLoading: Record<number, boolean> = {};
  difficultyDrafts: Record<number, number> = {};
  difficultyLoading: Record<number, boolean> = {};
  loading = false;
  errorMessage = '';
  todoMessage = '';

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
          this.syncDifficultyDrafts(projects);
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

  getTokenBudget(project: AdminProject) {
    return project.tokenBudget ?? project.token_budget ?? 100;
  }

  getTokenUsed(project: AdminProject) {
    return project.tokenUsed ?? project.token_used ?? 0;
  }

  getTokenRemaining(project: AdminProject) {
    return project.tokenRemaining ?? project.token_remaining ?? Math.max(this.getTokenBudget(project) - this.getTokenUsed(project), 0);
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
    return (project.todos || []).filter(todo => todo.done && !todo.settled);
  }

  getSettledTodos(project: AdminProject) {
    return (project.todos || []).filter(todo => todo.settled);
  }

  updateTodoDifficulty(project: AdminProject, todo: ProjectTodo) {
    const difficulty = this.getDifficultyDraft(todo);

    if (this.difficultyLoading[todo.id]) {
      return;
    }

    this.difficultyLoading[todo.id] = true;
    this.todoMessage = '';
    this.apiService.put<ProjectTodo>(
      `/admin/project-todos/${todo.id}/difficulty`,
      { difficulty },
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: updated => {
        this.projects = this.projects.map(item => item.id === project.id
          ? {
              ...item,
              todos: item.todos.map(projectTodo => projectTodo.id === updated.id ? updated : projectTodo)
            }
          : item
        );
        this.difficultyDrafts[updated.id] = this.getDifficultyDraft(updated);
        delete this.difficultyLoading[todo.id];
        this.todoMessage = 'adminProjects.feedback.difficultySaved';
        this.changeDetectorRef.detectChanges();
      },
      error: error => {
        this.todoMessage = error?.error?.error || 'adminProjects.feedback.difficultyFailure';
        delete this.difficultyLoading[todo.id];
        this.changeDetectorRef.detectChanges();
      }
    });
  }

  getPriorityLevel(priority: number) {
    return Math.min(4, Math.max(0, Number(priority ?? 0))) + 1;
  }

  getPriorityMultiplierLabel(priority: number) {
    const multipliers = [1, 1.1, 1.2, 1.35, 1.5];
    return `x${multipliers[this.getPriorityLevel(priority) - 1].toFixed(2)}`;
  }

  hasDifficultyChanged(todo: ProjectTodo) {
    return this.getDifficultyDraft(todo) !== Number(todo.difficulty);
  }

  get pendingProjects() {
    return this.projects.filter(project => project.review_status === 'pending');
  }

  reviewProject(project: AdminProject, action: 'approve' | 'reject') {
    if (project.review_status !== 'pending' || this.reviewLoading[project.id]) {
      return;
    }

    this.reviewLoading[project.id] = true;
    this.apiService.post<AdminProject>(
      `/admin/project-recruitments/${project.id}/review`,
      { action },
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: updated => {
        this.projects = this.projects.map(item => item.id === updated.id ? updated : item);
        delete this.reviewLoading[project.id];
        this.changeDetectorRef.detectChanges();
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'adminProjects.feedback.reviewFailure';
        delete this.reviewLoading[project.id];
        this.changeDetectorRef.detectChanges();
      }
    });
  }

  private syncDifficultyDrafts(projects: AdminProject[]) {
    for (const project of projects) {
      for (const todo of project.todos || []) {
        this.difficultyDrafts[todo.id] = this.getDifficultyDraft(todo);
      }
    }
  }

  private getDifficultyDraft(todo: ProjectTodo) {
    const difficulty = Number(this.difficultyDrafts[todo.id] ?? todo.difficulty);
    return this.difficultyOptions.includes(difficulty) ? difficulty : 6;
  }

}
