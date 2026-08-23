import { Component, ChangeDetectionStrategy } from '@angular/core';

//Tools
import { OnInit } from '@angular/core';
import { forkJoin } from 'rxjs';
import { TranslateService } from '@ngx-translate/core';
import { ApiService } from '../../../core/services/api.service';

// Models
import { Todo } from './todo.model';

interface ProjectTodoGroup {
  key: string;
  projectId: number | null;
  projectTitle: string;
  todos: Todo[];
  total: number;
  done: number;
}

interface ProjectRecruitmentMember {
  id: number;
  user: {
    id: number;
    username: string;
    nickname?: string;
  };
}

interface ProjectRecruitment {
  id: number;
  title: string;
  summary: string;
  creator: {
    id: number;
    username: string;
    nickname?: string;
  };
  members: ProjectRecruitmentMember[];
  member_count: number;
  owned_by_me: boolean;
  token_budget?: number;
  tokenBudget?: number;
  token_used?: number;
  tokenUsed?: number;
  token_remaining?: number;
  tokenRemaining?: number;
  review_status: 'open' | 'pending' | 'approved' | 'rejected';
}

interface ProjectTodoCard {
  key: string;
  projectId: number | null;
  projectTitle: string;
  summary?: string;
  memberCount?: number;
  project?: ProjectRecruitment;
  todos: Todo[];
  total: number;
  done: number;
  canPublish: boolean;
}

interface ProjectTodoPublishResponse {
  todos: Todo[];
  project?: Partial<ProjectRecruitment>;
  token_cost?: number;
  tokenCost?: number;
}

@Component({
  selector: 'app-todo',
  standalone: false,
  templateUrl: './todo.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './todo.component.css'
})
export class TodoComponent implements OnInit {
  private readonly projectFoldStorageKey = 'privateTodo.projectFolds.v1';
  private readonly projectGroupFoldStorageKey = 'privateTodo.projectGroupFolds.v1';
  readonly priorityMultipliers = [1.5, 1.35, 1.2, 1.1, 1];
  readonly timeOptions = [
    { value: 0, labelKey: 'privateTodo.time.lessThan30' },
    { value: 1, labelKey: 'privateTodo.time.oneHour' },
    { value: 2, labelKey: 'privateTodo.time.halfDay' },
    { value: 3, labelKey: 'privateTodo.time.oneDay' },
    { value: 5, labelKey: 'privateTodo.time.multipleDays' }
  ];
  todos: Todo[] = [];
  projectTodoGroups: ProjectTodoGroup[] = [];
  projects: ProjectRecruitment[] = [];
  newTodoText: string = '';
  currentUserId: number | null = null;
  todoLoading: Record<number, boolean> = {};
  todoTexts: Record<number, string> = {};
  todoTargets: Record<number, string> = {};
  todoPriorities: Record<number, number> = {};
  todoDifficulties: Record<number, number> = {};
  todoDurations: Record<number, number> = {};
  todoCompletionTimes: Record<number, number | null> = {};
  settlementLoading: Record<number, boolean> = {};
  projectFoldState: Record<string, boolean> = {};
  projectGroupFoldState: Record<string, boolean> = {};
  isAllTodosOpen = false;
  statusMessage = '';
  
  constructor(
    private apiService: ApiService,
    private translate: TranslateService
  ) {}

  ngOnInit() {
    this.loadProjectFoldState();
    this.loadProjectGroupFoldState();
    this.fetchTodos();
  }

  // C
  // 新增待辦事項
  addTodo() {
    if (!this.newTodoText.trim()) return;
    this.apiService.post<Todo>('/todos', { text: this.newTodoText }, this.apiService.createAuthHeaders())
      .subscribe(todo => {
        this.setTodos([...this.todos, todo]);
        this.newTodoText = '';
      });
  }
  
  // R
  // 取得所有待辦事項
  fetchTodos() {
    const headers = this.apiService.createAuthHeaders();

    forkJoin({
      assignedTodos: this.apiService.get<Todo[]>('/todos', headers),
      createdTodos: this.apiService.get<Todo[]>('/todos?created_by_me=true', headers),
      projects: this.apiService.get<ProjectRecruitment[]>('/project-recruitments', headers),
      currentUser: this.apiService.get<{ id: number }>('/me', headers),
    }).subscribe(({ assignedTodos, createdTodos, projects, currentUser }) => {
        this.currentUserId = currentUser.id;
        this.projects = projects;
        this.initializeProjectTodoDefaults(projects);
        this.setTodos(this.mergeTodos(assignedTodos, createdTodos));
      });
  }

  publishProjectTodo(project: ProjectRecruitment) {
    const text = (this.todoTexts[project.id] || '').trim();
    const target = this.todoTargets[project.id] || 'team';
    const priority = this.getProjectTodoPriority(project.id);

    if (!project.owned_by_me || !text || this.todoLoading[project.id]) {
      return;
    }

    const payload: {
      text: string;
      project_id: number;
      priority: number;
      difficulty: number;
      duration: number;
      assign_to_team?: boolean;
      assignee_user_id?: number;
    } = {
      text,
      project_id: project.id,
      priority,
      difficulty: 5,
      duration: 5,
    };

    if (target === 'team') {
      payload.assign_to_team = true;
    } else if (target === 'captain') {
      payload.assignee_user_id = project.creator.id;
    } else {
      payload.assignee_user_id = Number(target);
    }

    this.todoLoading[project.id] = true;
    this.apiService.post<Todo | Todo[] | ProjectTodoPublishResponse>(
      '/todos',
      payload,
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: result => {
        const createdTodos = this.getPublishedTodos(result);
        this.setTodos(this.mergeTodos(this.todos, createdTodos));
        this.updateProjectTokenState(project.id, this.getPublishedProject(result));
        this.todoTexts[project.id] = '';
        this.todoTargets[project.id] = 'team';
        this.todoPriorities[project.id] = 0;
        delete this.todoLoading[project.id];
        this.statusMessage = this.translate.instant('privateTodo.feedback.publishSuccess');
      },
      error: err => {
        this.statusMessage = err.error?.error || this.translate.instant('privateTodo.feedback.publishFailure');
        delete this.todoLoading[project.id];
      }
    });
  }
  
  // U
  // 更新待辦事項
  toggleClaim(todo: Todo) {
    this.apiService.put<Todo>(`/todos/${todo.id}`, {
      text: todo.text,
      claimed: !todo.claimed_by_id,
      priority: todo.priority,
      difficulty: todo.difficulty,
      duration: todo.duration
    }, this.apiService.createAuthHeaders()).subscribe(updated => {
      this.setTodos(this.todos.map(item => item.id === updated.id ? updated : item));
    });
  }

  toggleDone(todo: Todo) {
    const selectedDuration = this.getSelectedTodoDuration(todo);

    if (!todo.done && selectedDuration === null) {
      this.statusMessage = this.translate.instant('privateTodo.feedback.timeRequired');
      return;
    }

    this.apiService.put<Todo>(`/todos/${todo.id}`, {
      text: todo.text,
      done: !todo.done,
      priority: todo.priority,
      difficulty: todo.difficulty,
      duration: !todo.done ? selectedDuration : todo.duration
    }, this.apiService.createAuthHeaders()).subscribe(updated => {
      delete this.todoCompletionTimes[todo.id];
      this.setTodos(this.todos.map(item => item.id === updated.id ? updated : item));
    });
  }

  // D
  // 刪除待辦事項
  deleteTodo(id: number) {
    this.apiService.delete(`/todos/${id}`, this.apiService.createAuthHeaders())
      .subscribe(() => this.setTodos(this.todos.filter(t => t.id !== id)));
  }

  submitSettlementReview(project: ProjectRecruitment, todos: Todo[] = []) {
    if (!project.owned_by_me || !this.canSubmitSettlementReview(project, todos) || this.settlementLoading[project.id]) {
      return;
    }

    this.settlementLoading[project.id] = true;
    this.apiService.post<ProjectRecruitment>(
      `/project-recruitments/${project.id}/submit-review`,
      {},
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: updated => {
        this.projects = this.projects.map(item => item.id === updated.id ? updated : item);
        delete this.settlementLoading[project.id];
        this.statusMessage = this.translate.instant('privateTodo.settlement.submitted');
      },
      error: err => {
        this.statusMessage = err.error?.error || this.translate.instant('privateTodo.settlement.submitFailure');
        delete this.settlementLoading[project.id];
      }
    });
  }

  private setTodos(todos: Todo[]) {
    this.todos = todos;
    this.projectTodoGroups = this.buildProjectTodoGroups(todos);
  }

  private getPublishedTodos(result: Todo | Todo[] | ProjectTodoPublishResponse): Todo[] {
    if (Array.isArray(result)) {
      return result;
    }

    return 'todos' in result ? result.todos : [result];
  }

  private getPublishedProject(result: Todo | Todo[] | ProjectTodoPublishResponse) {
    return !Array.isArray(result) && 'project' in result ? result.project : undefined;
  }

  private updateProjectTokenState(projectId: number, tokenProject?: Partial<ProjectRecruitment>) {
    if (!tokenProject) {
      return;
    }

    this.projects = this.projects.map(project =>
      project.id === projectId ? { ...project, ...tokenProject } : project
    );
  }

  private buildProjectTodoGroups(todos: Todo[]): ProjectTodoGroup[] {
    const groups = todos
      .filter(todo => !!todo.project_id || !!todo.project_title)
      .reduce<Record<string, { projectId: number | null; projectTitle: string; todos: Todo[] }>>((grouped, todo) => {
        const projectId = todo.project_id ?? null;
        const projectTitle = todo.project_title || 'Unsorted Project';
        const groupKey = `${projectId ?? 'none'}:${projectTitle}`;

        grouped[groupKey] ??= { projectId, projectTitle, todos: [] };
        grouped[groupKey].todos.push(todo);

        return grouped;
      }, {});

    return Object.entries(groups)
      .map(([key, group]) => ({
        key,
        projectId: group.projectId,
        projectTitle: group.projectTitle,
        todos: [...group.todos].sort((a, b) =>
          Number(a.done) - Number(b.done) ||
          this.getTodoPriority(a) - this.getTodoPriority(b) ||
          a.text.localeCompare(b.text)
        ),
        total: group.todos.length,
        done: group.todos.filter(todo => todo.done).length,
      }))
      .sort((a, b) =>
        a.projectTitle.localeCompare(b.projectTitle) ||
        Number(a.projectId ?? 0) - Number(b.projectId ?? 0)
      );
  }

  private mergeTodos(...todoLists: Todo[][]) {
    const merged = new Map<number, Todo>();

    for (const todo of todoLists.flat()) {
      merged.set(todo.id, todo);
    }

    return [...merged.values()].sort((a, b) =>
      Number(a.done) - Number(b.done) ||
      this.getTodoPriority(a) - this.getTodoPriority(b) ||
      (b.created_at || '').localeCompare(a.created_at || '') ||
      b.id - a.id
    );
  }

  private initializeProjectTodoDefaults(projects: ProjectRecruitment[]) {
    for (const project of projects) {
      this.todoTargets[project.id] ??= 'team';
      this.todoPriorities[project.id] ??= 0;
    }
  }

  getTodoPriority(todo: Todo) {
    return Math.min(4, Math.max(0, Number(todo.priority ?? 0)));
  }

  getTodoDifficulty(todo: Todo) {
    return Math.min(13, Math.max(0, Number(todo.difficulty ?? 5)));
  }

  getTodoDuration(todo: Todo) {
    return Math.min(9, Math.max(0, Number(todo.duration ?? 5)));
  }

  getLevelColor(level: number) {
    const value = Math.min(9, Math.max(0, Number(level)));
    return `hsl(${(value / 9) * 120}, 78%, 46%)`;
  }

  getPriorityColor(priority: number) {
    const value = this.getTodoPriority({ priority } as Todo);
    return `hsl(${120 - (value / 4) * 120}, 78%, 46%)`;
  }

  getPriorityLevel(priority: number) {
    return this.getTodoPriority({ priority } as Todo) + 1;
  }

  getPriorityMultiplier(priority: number) {
    return this.priorityMultipliers[this.getTodoPriority({ priority } as Todo)];
  }

  getPriorityMultiplierLabel(priority: number) {
    return `x${this.getPriorityMultiplier(priority).toFixed(2)}`;
  }

  getEffortColor(level: number) {
    return this.getLevelColor(level);
  }

  getProjectTodoPriority(projectId: number) {
    const priority = Number(this.todoPriorities[projectId] ?? 0);
    return Math.min(4, Math.max(0, priority));
  }

  getProjectTodoDifficulty(projectId: number) {
    const difficulty = Number(this.todoDifficulties[projectId] ?? 5);
    return Math.min(9, Math.max(0, difficulty));
  }

  getProjectTodoDuration(projectId: number) {
    const duration = Number(this.todoDurations[projectId] ?? 5);
    return Math.min(9, Math.max(0, duration));
  }

  canToggleClaim(todo: Todo) {
    return !todo.done && (!todo.claimed_by_id || todo.claimed_by_id === this.currentUserId);
  }

  canToggleDone(todo: Todo) {
    return todo.claimed_by_id === this.currentUserId && (todo.done || this.hasSelectedTodoDuration(todo));
  }

  canSubmitSettlementReview(project: ProjectRecruitment, todos: Todo[] = []) {
    return project.review_status !== 'pending' && this.getReviewPendingTodos(todos).length > 0;
  }

  getProjectTokenUsed(project?: ProjectRecruitment) {
    return project?.tokenUsed ?? project?.token_used ?? 0;
  }

  getProjectTokenRemaining(project?: ProjectRecruitment) {
    if (!project) {
      return 0;
    }

    return project.tokenRemaining ?? project.token_remaining ?? Math.max((project.tokenBudget ?? project.token_budget ?? 100) - this.getProjectTokenUsed(project), 0);
  }

  getPendingCompletionTodos(todos: Todo[]): Todo[] {
    return todos.filter(todo => !todo.done);
  }

  getReviewPendingTodos(todos: Todo[]): Todo[] {
    return todos.filter(todo => todo.done && !todo.settled);
  }

  getSettledTodos(todos: Todo[]): Todo[] {
    return todos.filter(todo => todo.settled);
  }

  getSelectedTodoDuration(todo: Todo) {
    const duration = this.todoCompletionTimes[todo.id];
    if (duration === undefined || duration === null) {
      return null;
    }

    const value = Number(duration);
    return Number.isNaN(value) ? null : value;
  }

  hasSelectedTodoDuration(todo: Todo) {
    return this.getSelectedTodoDuration(todo) !== null;
  }

  toggleAllTodos() {
    this.isAllTodosOpen = !this.isAllTodosOpen;
  }

  isProjectCardOpen(projectKey: string) {
    return this.projectFoldState[projectKey] ?? true;
  }

  toggleProjectCard(projectKey: string) {
    this.projectFoldState = {
      ...this.projectFoldState,
      [projectKey]: !this.isProjectCardOpen(projectKey)
    };
    this.saveProjectFoldState();
  }

  isProjectGroupOpen(projectKey: string, groupKey: string, defaultOpen = true) {
    return this.projectGroupFoldState[this.getProjectGroupFoldKey(projectKey, groupKey)] ?? defaultOpen;
  }

  setProjectGroupOpen(projectKey: string, groupKey: string, event: Event) {
    const details = event.target as HTMLDetailsElement;
    this.projectGroupFoldState = {
      ...this.projectGroupFoldState,
      [this.getProjectGroupFoldKey(projectKey, groupKey)]: details.open
    };
    this.saveProjectGroupFoldState();
  }

  private loadProjectFoldState() {
    this.projectFoldState = this.readBooleanMap(this.projectFoldStorageKey);
  }

  private saveProjectFoldState() {
    this.writeBooleanMap(this.projectFoldStorageKey, this.projectFoldState);
  }

  private loadProjectGroupFoldState() {
    this.projectGroupFoldState = this.readBooleanMap(this.projectGroupFoldStorageKey);
  }

  private saveProjectGroupFoldState() {
    this.writeBooleanMap(this.projectGroupFoldStorageKey, this.projectGroupFoldState);
  }

  private getProjectGroupFoldKey(projectKey: string, groupKey: string) {
    return `${projectKey}:${groupKey}`;
  }

  private readBooleanMap(storageKey: string): Record<string, boolean> {
    try {
      const value = JSON.parse(localStorage.getItem(storageKey) || '{}');
      return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    } catch {
      return {};
    }
  }

  private writeBooleanMap(storageKey: string, value: Record<string, boolean>) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(value));
    } catch {
      // Ignore storage failures so the Todo page remains usable in restricted browsers.
    }
  }

  get completedTodoCount() {
    return this.todos.filter(todo => todo.done).length;
  }

  get ownedProjects() {
    return this.projects.filter(project => project.owned_by_me);
  }

  get projectTodoCards(): ProjectTodoCard[] {
    const cards = new Map<string, ProjectTodoCard>();

    for (const project of this.ownedProjects) {
      const key = String(project.id);
      cards.set(key, {
        key,
        projectId: project.id,
        projectTitle: project.title,
        summary: project.summary,
        memberCount: project.member_count,
        project,
        todos: [],
        total: 0,
        done: 0,
        canPublish: true
      });
    }

    for (const group of this.projectTodoGroups) {
      const key = String(group.projectId ?? group.key);
      const project = group.projectId ? this.projects.find(item => item.id === group.projectId) : undefined;
      const existing = cards.get(key);

      cards.set(key, {
        key,
        projectId: group.projectId,
        projectTitle: project?.title || group.projectTitle,
        summary: project?.summary || existing?.summary,
        memberCount: project?.member_count ?? existing?.memberCount,
        project: project || existing?.project,
        todos: group.todos,
        total: group.total,
        done: group.done,
        canPublish: !!(project || existing?.project)?.owned_by_me
      });
    }

    return [...cards.values()].sort((a, b) =>
      Number(!a.canPublish) - Number(!b.canPublish) ||
      a.projectTitle.localeCompare(b.projectTitle)
    );
  }
}
