import { ChangeDetectorRef, Component, NgZone, OnDestroy, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { merge, of, Subject, timer } from 'rxjs';
import { catchError, filter, map, switchMap, take, takeUntil, tap, timeout } from 'rxjs/operators';
import { AuditLogItem, AuditLogService } from '../../../core/services/audit-log.service';

type AuditLogGroupKey = 'register' | 'project' | 'signIn' | 'content' | 'news' | 'todoSettlement';
type AuditLogSectionKey = 'admin';

interface AuditLogGroup {
  key: AuditLogGroupKey;
  accent: string;
  logs: AuditLogItem[];
}

interface AuditLogSection {
  key: AuditLogSectionKey;
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
  expandedRawLogs: Record<string, boolean> = {};
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
      key: 'admin',
      groups: [
        {
          key: 'content',
          accent: 'var(--studio-danger)',
          logs: []
        },
        {
          key: 'news',
          accent: 'var(--studio-accent)',
          logs: []
        },
        {
          key: 'todoSettlement',
          accent: '#facc15',
          logs: []
        }
      ]
    }
  ];

  constructor(
    private auditLogService: AuditLogService,
    private translate: TranslateService,
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
    return group.key === 'register';
  }

  isProjectGroup(group: AuditLogGroup) {
    return group.key === 'project';
  }

  isSignInGroup(group: AuditLogGroup) {
    return group.key === 'signIn';
  }

  isContentGroup(group: AuditLogGroup) {
    return group.key === 'content';
  }

  isNewsGroup(group: AuditLogGroup) {
    return group.key === 'news';
  }

  isTodoSettlementGroup(group: AuditLogGroup) {
    return group.key === 'todoSettlement';
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
    return `${section.key}.${group.key}`;
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
  getRawLogKey(group: AuditLogGroup, log: AuditLogItem) {
    return `${group.key}.${log.id || log.time + log.actor + log.action + log.target}`;
  }

  isRawLogExpanded(group: AuditLogGroup, log: AuditLogItem) {
    return !!this.expandedRawLogs[this.getRawLogKey(group, log)];
  }

  toggleRawLog(event: Event, group: AuditLogGroup, log: AuditLogItem) {
    event.stopPropagation();
    const key = this.getRawLogKey(group, log);
    this.expandedRawLogs = {
      ...this.expandedRawLogs,
      [key]: !this.expandedRawLogs[key]
    };
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
          catchError(() => of({ response: null, error: this.translate.instant('superadminLogs.feedback.registerLoadFailed') }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.registerItems = Array.isArray(response.items) ? response.items : [];
          this.registerSource = this.formatSource(response.path, response.count ?? this.registerItems.length);
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
          catchError(() => of({ response: null, error: this.translate.instant('superadminLogs.feedback.projectLoadFailed') }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.projectItems = Array.isArray(response.items) ? response.items : [];
          this.projectSource = this.formatSource(response.path, response.count ?? this.projectItems.length);
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
          catchError(() => of({ response: null, error: this.translate.instant('superadminLogs.feedback.signInLoadFailed') }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.signInItems = Array.isArray(response.items) ? response.items : [];
          this.signInSource = this.formatSource(response.path, response.count ?? this.signInItems.length);
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
          catchError(() => of({ response: null, error: this.translate.instant('superadminLogs.feedback.contentLoadFailed') }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.contentItems = Array.isArray(response.items) ? response.items : [];
          this.contentSource = this.formatSource(response.path, response.count ?? this.contentItems.length);
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
          catchError(() => of({ response: null, error: this.translate.instant('superadminLogs.feedback.newsLoadFailed') }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.newsItems = Array.isArray(response.items) ? response.items : [];
          this.newsSource = this.formatSource(response.path, response.count ?? this.newsItems.length);
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
          catchError(() => of({ response: null, error: this.translate.instant('superadminLogs.feedback.todoSettlementLoadFailed') }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          this.todoSettlementItems = Array.isArray(response.items) ? response.items : [];
          this.todoSettlementSource = this.formatSource(response.path, response.count ?? this.todoSettlementItems.length);
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

  private formatSource(path: string | undefined, count: number) {
    if (!path) {
      return '';
    }

    return this.translate.instant('superadminLogs.source.records', { path, count });
  }

  private getCollapsedStorageKey(key: string) {
    return `${this.collapsedStoragePrefix}.${key}`;
  }
}
