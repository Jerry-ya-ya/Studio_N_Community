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

@Component({
  selector: 'app-todo',
  standalone: false,
  templateUrl: './todo.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './todo.component.css'
})
export class TodoComponent implements OnInit {
  todos: Todo[] = [];
  projectTodoGroups: ProjectTodoGroup[] = [];
  projects: ProjectRecruitment[] = [];
  newTodoText: string = '';
  currentUserId: number | null = null;
  todoLoading: Record<number, boolean> = {};
  todoTexts: Record<number, string> = {};
  todoTargets: Record<number, string> = {};
  todoPriorities: Record<number, number> = {};
  isAllTodosOpen = false;
  statusMessage = '';
  
  constructor(
    private apiService: ApiService,
    private translate: TranslateService
  ) {}

  ngOnInit() {
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
      assign_to_team?: boolean;
      assignee_user_id?: number;
    } = {
      text,
      project_id: project.id,
      priority,
    };

    if (target === 'team') {
      payload.assign_to_team = true;
    } else if (target === 'captain') {
      payload.assignee_user_id = project.creator.id;
    } else {
      payload.assignee_user_id = Number(target);
    }

    this.todoLoading[project.id] = true;
    this.apiService.post<Todo | Todo[]>(
      '/todos',
      payload,
      this.apiService.createAuthHeaders()
    ).subscribe({
      next: result => {
        const createdTodos = Array.isArray(result) ? result : [result];
        this.setTodos(this.mergeTodos(this.todos, createdTodos));
        this.todoTexts[project.id] = '';
        this.todoTargets[project.id] = 'team';
        this.todoPriorities[project.id] = 5;
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
      priority: todo.priority
    }, this.apiService.createAuthHeaders()).subscribe(updated => {
      this.setTodos(this.todos.map(item => item.id === updated.id ? updated : item));
    });
  }

  toggleDone(todo: Todo) {
    this.apiService.put<Todo>(`/todos/${todo.id}`, {
      text: todo.text,
      done: !todo.done,
      priority: todo.priority
    }, this.apiService.createAuthHeaders()).subscribe(updated => {
      this.setTodos(this.todos.map(item => item.id === updated.id ? updated : item));
    });
  }

  // D
  // 刪除待辦事項
  deleteTodo(id: number) {
    this.apiService.delete(`/todos/${id}`, this.apiService.createAuthHeaders())
      .subscribe(() => this.setTodos(this.todos.filter(t => t.id !== id)));
  }

  private setTodos(todos: Todo[]) {
    this.todos = todos;
    this.projectTodoGroups = this.buildProjectTodoGroups(todos);
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

  getTodoPriority(todo: Todo) {
    return Math.min(9, Math.max(0, Number(todo.priority ?? 5)));
  }

  getPriorityColor(priority: number) {
    const level = Math.min(9, Math.max(0, Number(priority)));
    return `hsl(${(level / 9) * 120}, 78%, 46%)`;
  }

  getProjectTodoPriority(projectId: number) {
    const priority = Number(this.todoPriorities[projectId] ?? 5);
    return Math.min(9, Math.max(0, priority));
  }

  canToggleClaim(todo: Todo) {
    return !todo.done && (!todo.claimed_by_id || todo.claimed_by_id === this.currentUserId);
  }

  toggleAllTodos() {
    this.isAllTodosOpen = !this.isAllTodosOpen;
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
