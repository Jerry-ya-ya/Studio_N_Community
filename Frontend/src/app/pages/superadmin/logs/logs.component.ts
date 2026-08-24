import { ChangeDetectorRef, Component, NgZone, OnDestroy, OnInit } from '@angular/core';
import { merge, of, Subject, timer } from 'rxjs';
import { catchError, filter, map, switchMap, take, takeUntil, tap, timeout } from 'rxjs/operators';
import { AuditLogItem, AuditLogService } from '../../../core/services/audit-log.service';

interface AuditLogGroup {
  title: string;
  description: string;
  accent: string;
  logs: AuditLogItem[];
}

interface AuditLogSection {
  title: string;
  eyebrow: string;
  description: string;
  groups: AuditLogGroup[];
}

@Component({
  selector: 'app-logs',
  standalone: false,
  templateUrl: './logs.component.html',
  styleUrl: './logs.component.css',
})
export class LogsComponent implements OnInit, OnDestroy {
  registerItems: AuditLogItem[] = [];
  registerLoading = false;
  registerError = '';
  registerSource = '';
  projectItems: AuditLogItem[] = [];
  projectLoading = false;
  projectError = '';
  projectSource = '';
  signInItems: AuditLogItem[] = [];
  signInLoading = false;
  signInError = '';
  signInSource = '';
  contentItems: AuditLogItem[] = [];
  contentLoading = false;
  contentError = '';
  contentSource = '';
  newsItems: AuditLogItem[] = [];
  newsLoading = false;
  newsError = '';
  newsSource = '';
  todoSettlementItems: AuditLogItem[] = [];
  todoSettlementLoading = false;
  todoSettlementError = '';
  todoSettlementSource = '';
  collapsedGroups: Record<string, boolean> = {};
  private destroy$ = new Subject<void>();
  private refreshRegisterLogs$ = new Subject<void>();
  private refreshProjectLogs$ = new Subject<void>();
  private refreshSignInLogs$ = new Subject<void>();
  private refreshContentLogs$ = new Subject<void>();
  private refreshNewsLogs$ = new Subject<void>();
  private refreshTodoSettlementLogs$ = new Subject<void>();
  private readonly collapsedStoragePrefix = 'superadmin.logs.collapsed';

  sections: AuditLogSection[] = [
    {
      title: 'Admin',
      eyebrow: 'Management Activity',
      description: 'Administrative records for homepage content and news changes.',
      groups: [
        {
          title: 'Content Log',
          description: 'Tracks who modified public home content.',
          accent: 'var(--studio-danger)',
          logs: []
        },
        {
          title: 'News Log',
          description: 'Tracks who modified news content or background assets.',
          accent: 'var(--studio-accent)',
          logs: []
        },
        {
          title: 'Todo Settlement Log',
          description: 'Tracks Todo reward settlement parameters, formulas, coins, and reviewers.',
          accent: 'var(--studio-warning)',
          logs: []
        }
      ]
    }
  ];

  constructor(
    private auditLogService: AuditLogService,
    private zone: NgZone,
    private changeDetector: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadCollapsedGroups();
    this.initializeContentLogStream();
    this.initializeNewsLogStream();
    this.initializeTodoSettlementLogStream();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  get totalLogTypes() {
    return this.sections.reduce((total, section) => total + section.groups.length, 0);
  }

  get totalPreviewRows() {
    return this.sections.reduce(
      (total, section) => total + section.groups.reduce((groupTotal, group) => groupTotal + this.getGroupLogs(group).length, 0),
      0
    );
  }

  retryGroup(group: AuditLogGroup) {
    if (this.isRegisterGroup(group)) {
      this.loadRegisterLogs();
    }
    if (this.isProjectGroup(group)) {
      this.loadProjectLogs();
    }
    if (this.isSignInGroup(group)) {
      this.loadSignInLogs();
    }
    if (this.isContentGroup(group)) {
      this.loadContentLogs();
    }
    if (this.isNewsGroup(group)) {
      this.loadNewsLogs();
    }
    if (this.isTodoSettlementGroup(group)) {
      this.loadTodoSettlementLogs();
    }
  }

  isRegisterGroup(group: AuditLogGroup) {
    return group.title === 'Register Log';
  }

  isProjectGroup(group: AuditLogGroup) {
    return group.title === 'Project Log';
  }

  isSignInGroup(group: AuditLogGroup) {
    return group.title === 'Sign In Log';
  }

  isContentGroup(group: AuditLogGroup) {
    return group.title === 'Content Log';
  }

  isNewsGroup(group: AuditLogGroup) {
    return group.title === 'News Log';
  }

  isTodoSettlementGroup(group: AuditLogGroup) {
    return group.title === 'Todo Settlement Log';
  }

  isLiveLogGroup(group: AuditLogGroup) {
    return (
      this.isRegisterGroup(group) ||
      this.isProjectGroup(group) ||
      this.isSignInGroup(group) ||
      this.isContentGroup(group) ||
      this.isNewsGroup(group) ||
      this.isTodoSettlementGroup(group)
    );
  }

  getGroupLogs(group: AuditLogGroup) {
    if (this.isRegisterGroup(group)) {
      return this.registerItems;
    }
    if (this.isProjectGroup(group)) {
      return this.projectItems;
    }
    if (this.isSignInGroup(group)) {
      return this.signInItems;
    }
    if (this.isContentGroup(group)) {
      return this.contentItems;
    }
    if (this.isNewsGroup(group)) {
      return this.newsItems;
    }
    if (this.isTodoSettlementGroup(group)) {
      return this.todoSettlementItems;
    }
    return group.logs;
  }

  getGroupSource(group: AuditLogGroup) {
    if (this.isRegisterGroup(group)) {
      return this.registerSource;
    }
    if (this.isProjectGroup(group)) {
      return this.projectSource;
    }
    if (this.isSignInGroup(group)) {
      return this.signInSource;
    }
    if (this.isContentGroup(group)) {
      return this.contentSource;
    }
    if (this.isNewsGroup(group)) {
      return this.newsSource;
    }
    if (this.isTodoSettlementGroup(group)) {
      return this.todoSettlementSource;
    }
    return '';
  }

  isGroupLoading(group: AuditLogGroup) {
    return (
      (this.isRegisterGroup(group) && this.registerLoading) ||
      (this.isProjectGroup(group) && this.projectLoading) ||
      (this.isSignInGroup(group) && this.signInLoading) ||
      (this.isContentGroup(group) && this.contentLoading) ||
      (this.isNewsGroup(group) && this.newsLoading) ||
      (this.isTodoSettlementGroup(group) && this.todoSettlementLoading)
    );
  }

  getGroupError(group: AuditLogGroup) {
    if (this.isRegisterGroup(group)) {
      return this.registerError;
    }
    if (this.isProjectGroup(group)) {
      return this.projectError;
    }
    if (this.isSignInGroup(group)) {
      return this.signInError;
    }
    if (this.isContentGroup(group)) {
      return this.contentError;
    }
    if (this.isNewsGroup(group)) {
      return this.newsError;
    }
    if (this.isTodoSettlementGroup(group)) {
      return this.todoSettlementError;
    }
    return '';
  }

  getGroupKey(section: AuditLogSection, group: AuditLogGroup) {
    return `${section.title}.${group.title}`.replace(/\s+/g, '-').toLowerCase();
  }

  isGroupCollapsed(section: AuditLogSection, group: AuditLogGroup) {
    return !!this.collapsedGroups[this.getGroupKey(section, group)];
  }

  toggleGroup(section: AuditLogSection, group: AuditLogGroup) {
    const key = this.getGroupKey(section, group);
    this.collapsedGroups = {
      ...this.collapsedGroups,
      [key]: !this.collapsedGroups[key]
    };
    this.saveCollapsedGroup(key, this.collapsedGroups[key]);
  }

  toggleGroupFromKeyboard(event: Event, section: AuditLogSection, group: AuditLogGroup) {
    event.preventDefault();
    this.toggleGroup(section, group);
  }

  getLogPayload(log: AuditLogItem): Record<string, unknown> | null {
    return log.rawJson || log.raw_json || null;
  }

  getSettlementField(log: AuditLogItem, key: string) {
    const payload = this.getLogPayload(log);
    const value = payload?.[key];
    return value === undefined || value === null || value === '' ? '-' : String(value);
  }
  loadRegisterLogs() {
    this.refreshRegisterLogs$.next();
  }

  loadProjectLogs() {
    this.refreshProjectLogs$.next();
  }

  loadSignInLogs() {
    this.refreshSignInLogs$.next();
  }

  loadContentLogs() {
    this.refreshContentLogs$.next();
  }

  loadNewsLogs() {
    this.refreshNewsLogs$.next();
  }

  loadTodoSettlementLogs() {
    this.refreshTodoSettlementLogs$.next();
  }

  refreshGroup(group: AuditLogGroup) {
    if (this.isRegisterGroup(group)) {
      this.loadRegisterLogs();
    }
    if (this.isProjectGroup(group)) {
      this.loadProjectLogs();
    }
    if (this.isSignInGroup(group)) {
      this.loadSignInLogs();
    }
    if (this.isContentGroup(group)) {
      this.loadContentLogs();
    }
    if (this.isNewsGroup(group)) {
      this.loadNewsLogs();
    }
    if (this.isTodoSettlementGroup(group)) {
      this.loadTodoSettlementLogs();
    }
  }

  private initializeRegisterLogStream() {
    const initialRetry$ = timer(0, 1000).pipe(
      take(8),
      filter(() => !this.registerItems.length)
    );

    merge(initialRetry$, this.refreshRegisterLogs$).pipe(
      takeUntil(this.destroy$),
      tap(() => {
        this.registerLoading = true;
        this.registerError = '';
      }),
      switchMap(() =>
        this.auditLogService.getRegisterLogs().pipe(
          timeout(10000),
          map(response => ({ response, error: '' })),
          catchError(() => of({ response: null, error: 'Unable to load register logs.' }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.registerItems = Array.isArray(response.items) ? response.items : [];
          this.registerSource = response.path ? `${response.path} / ${response.count ?? this.registerItems.length} records` : '';
          this.registerError = '';
        } else {
          this.registerItems = [];
          this.registerSource = '';
          this.registerError = error;
        }

        this.registerLoading = false;
        this.changeDetector.detectChanges();
      });
    });
  }

  private initializeProjectLogStream() {
    const initialRetry$ = timer(0, 1000).pipe(
      take(8),
      filter(() => !this.projectItems.length)
    );

    merge(initialRetry$, this.refreshProjectLogs$).pipe(
      takeUntil(this.destroy$),
      tap(() => {
        this.projectLoading = true;
        this.projectError = '';
      }),
      switchMap(() =>
        this.auditLogService.getProjectLogs().pipe(
          timeout(10000),
          map(response => ({ response, error: '' })),
          catchError(() => of({ response: null, error: 'Unable to load project logs.' }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.projectItems = Array.isArray(response.items) ? response.items : [];
          this.projectSource = response.path ? `${response.path} / ${response.count ?? this.projectItems.length} records` : '';
          this.projectError = '';
        } else {
          this.projectItems = [];
          this.projectSource = '';
          this.projectError = error;
        }

        this.projectLoading = false;
        this.changeDetector.detectChanges();
      });
    });
  }

  private initializeSignInLogStream() {
    const initialRetry$ = timer(0, 1000).pipe(
      take(8),
      filter(() => !this.signInItems.length)
    );

    merge(initialRetry$, this.refreshSignInLogs$).pipe(
      takeUntil(this.destroy$),
      tap(() => {
        this.signInLoading = true;
        this.signInError = '';
      }),
      switchMap(() =>
        this.auditLogService.getSignInLogs().pipe(
          timeout(10000),
          map(response => ({ response, error: '' })),
          catchError(() => of({ response: null, error: 'Unable to load sign in logs.' }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.signInItems = Array.isArray(response.items) ? response.items : [];
          this.signInSource = response.path ? `${response.path} / ${response.count ?? this.signInItems.length} records` : '';
          this.signInError = '';
        } else {
          this.signInItems = [];
          this.signInSource = '';
          this.signInError = error;
        }

        this.signInLoading = false;
        this.changeDetector.detectChanges();
      });
    });
  }

  private initializeContentLogStream() {
    const initialRetry$ = timer(0, 1000).pipe(
      take(8),
      filter(() => !this.contentItems.length)
    );

    merge(initialRetry$, this.refreshContentLogs$).pipe(
      takeUntil(this.destroy$),
      tap(() => {
        this.contentLoading = true;
        this.contentError = '';
      }),
      switchMap(() =>
        this.auditLogService.getContentLogs().pipe(
          timeout(10000),
          map(response => ({ response, error: '' })),
          catchError(() => of({ response: null, error: 'Unable to load content logs.' }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.contentItems = Array.isArray(response.items) ? response.items : [];
          this.contentSource = response.path ? `${response.path} / ${response.count ?? this.contentItems.length} records` : '';
          this.contentError = '';
        } else {
          this.contentItems = [];
          this.contentSource = '';
          this.contentError = error;
        }

        this.contentLoading = false;
        this.changeDetector.detectChanges();
      });
    });
  }

  private initializeNewsLogStream() {
    const initialRetry$ = timer(0, 1000).pipe(
      take(8),
      filter(() => !this.newsItems.length)
    );

    merge(initialRetry$, this.refreshNewsLogs$).pipe(
      takeUntil(this.destroy$),
      tap(() => {
        this.newsLoading = true;
        this.newsError = '';
      }),
      switchMap(() =>
        this.auditLogService.getNewsLogs().pipe(
          timeout(10000),
          map(response => ({ response, error: '' })),
          catchError(() => of({ response: null, error: 'Unable to load news logs.' }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.newsItems = Array.isArray(response.items) ? response.items : [];
          this.newsSource = response.path ? `${response.path} / ${response.count ?? this.newsItems.length} records` : '';
          this.newsError = '';
        } else {
          this.newsItems = [];
          this.newsSource = '';
          this.newsError = error;
        }

        this.newsLoading = false;
        this.changeDetector.detectChanges();
      });
    });
  }

  private initializeTodoSettlementLogStream() {
    const initialRetry$ = timer(0, 1000).pipe(
      take(8),
      filter(() => !this.todoSettlementItems.length)
    );

    merge(initialRetry$, this.refreshTodoSettlementLogs$).pipe(
      takeUntil(this.destroy$),
      tap(() => {
        this.todoSettlementLoading = true;
        this.todoSettlementError = '';
      }),
      switchMap(() =>
        this.auditLogService.getTodoSettlementLogs().pipe(
          timeout(10000),
          map(response => ({ response, error: '' })),
          catchError(() => of({ response: null, error: 'Unable to load todo settlement logs.' }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.todoSettlementItems = Array.isArray(response.items) ? response.items : [];
          this.todoSettlementSource = response.path ? `${response.path} / ${response.count ?? this.todoSettlementItems.length} records` : '';
          this.todoSettlementError = '';
        } else {
          this.todoSettlementItems = [];
          this.todoSettlementSource = '';
          this.todoSettlementError = error;
        }

        this.todoSettlementLoading = false;
        this.changeDetector.detectChanges();
      });
    });
  }

  private loadCollapsedGroups() {
    const nextState: Record<string, boolean> = {};

    for (const section of this.sections) {
      for (const group of section.groups) {
        const key = this.getGroupKey(section, group);
        nextState[key] = localStorage.getItem(this.getCollapsedStorageKey(key)) === 'true';
      }
    }

    this.collapsedGroups = nextState;
  }

  private saveCollapsedGroup(key: string, collapsed: boolean) {
    localStorage.setItem(this.getCollapsedStorageKey(key), String(collapsed));
  }

  private getCollapsedStorageKey(key: string) {
    return `${this.collapsedStoragePrefix}.${key}`;
  }
}
