import { ChangeDetectorRef, Component, NgZone, OnDestroy, OnInit } from '@angular/core';
import { merge, of, Subject, timer } from 'rxjs';
import { catchError, filter, map, switchMap, take, takeUntil, tap, timeout } from 'rxjs/operators';
import { AuditLogItem, AuditLogService } from '../../../core/services/audit-log.service';

interface AuditLogGroup {
  key: 'register' | 'project' | 'signIn';
  titleKey: string;
  descriptionKey: string;
  accent: string;
  logs: AuditLogItem[];
  loading: boolean;
  error: string;
  source: string;
  sourceCount: number;
  refresh$: Subject<void>;
}

@Component({
  selector: 'app-logs',
  standalone: false,
  templateUrl: './logs.component.html',
  styleUrl: './logs.component.css',
})
export class LogsComponent implements OnInit, OnDestroy {
  groups: AuditLogGroup[] = [
    {
      key: 'register',
      titleKey: 'adminLogs.groups.register.title',
      descriptionKey: 'adminLogs.groups.register.description',
      accent: 'var(--studio-success)',
      logs: [],
      loading: false,
      error: '',
      source: '',
      sourceCount: 0,
      refresh$: new Subject<void>()
    },
    {
      key: 'project',
      titleKey: 'adminLogs.groups.project.title',
      descriptionKey: 'adminLogs.groups.project.description',
      accent: 'var(--studio-accent)',
      logs: [],
      loading: false,
      error: '',
      source: '',
      sourceCount: 0,
      refresh$: new Subject<void>()
    },
    {
      key: 'signIn',
      titleKey: 'adminLogs.groups.signIn.title',
      descriptionKey: 'adminLogs.groups.signIn.description',
      accent: 'var(--studio-warm)',
      logs: [],
      loading: false,
      error: '',
      source: '',
      sourceCount: 0,
      refresh$: new Subject<void>()
    }
  ];

  collapsedGroups: Record<string, boolean> = {};
  expandedRawLogs: Record<string, boolean> = {};
  private destroy$ = new Subject<void>();
  private readonly collapsedStoragePrefix = 'admin.logs.collapsed';

  constructor(
    private auditLogService: AuditLogService,
    private zone: NgZone,
    private changeDetector: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadCollapsedGroups();
    for (const group of this.groups) {
      this.initializeLogStream(group);
    }
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
    for (const group of this.groups) {
      group.refresh$.complete();
    }
  }

  get totalLogTypes() {
    return this.groups.length;
  }

  get totalPreviewRows() {
    return this.groups.reduce((total, group) => total + group.logs.length, 0);
  }

  isGroupCollapsed(group: AuditLogGroup) {
    return !!this.collapsedGroups[this.getGroupKey(group)];
  }

  toggleGroup(group: AuditLogGroup) {
    const key = this.getGroupKey(group);
    this.collapsedGroups = {
      ...this.collapsedGroups,
      [key]: !this.collapsedGroups[key]
    };
    localStorage.setItem(this.getCollapsedStorageKey(key), String(this.collapsedGroups[key]));
  }

  toggleGroupFromKeyboard(event: Event, group: AuditLogGroup) {
    event.preventDefault();
    this.toggleGroup(group);
  }

  refreshGroup(group: AuditLogGroup) {
    group.refresh$.next();
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

  private initializeLogStream(group: AuditLogGroup) {
    const initialRetry$ = timer(0, 1000).pipe(
      take(8),
      filter(() => !group.logs.length)
    );

    merge(initialRetry$, group.refresh$).pipe(
      takeUntil(this.destroy$),
      tap(() => {
        group.loading = true;
        group.error = '';
      }),
      switchMap(() =>
        this.fetchGroupLogs(group).pipe(
          timeout(10000),
          map(response => ({ response, error: '' })),
          catchError(() => of({ response: null, error: 'adminLogs.state.loadError' }))
        )
      )
    ).subscribe(({ response, error }) => {
      this.zone.run(() => {
        if (response) {
          group.logs = Array.isArray(response.items) ? response.items : [];
          group.source = response.path || '';
          group.sourceCount = response.count ?? group.logs.length;
          group.error = '';
        } else {
          group.logs = [];
          group.source = '';
          group.sourceCount = 0;
          group.error = error;
        }

        group.loading = false;
        this.changeDetector.detectChanges();
      });
    });
  }

  private fetchGroupLogs(group: AuditLogGroup) {
    if (group.key === 'register') {
      return this.auditLogService.getRegisterLogs();
    }
    if (group.key === 'project') {
      return this.auditLogService.getProjectLogs();
    }
    return this.auditLogService.getSignInLogs();
  }

  private loadCollapsedGroups() {
    const nextState: Record<string, boolean> = {};

    for (const group of this.groups) {
      const key = this.getGroupKey(group);
      nextState[key] = localStorage.getItem(this.getCollapsedStorageKey(key)) === 'true';
    }

    this.collapsedGroups = nextState;
  }

  private getGroupKey(group: AuditLogGroup) {
    return group.key;
  }

  private getCollapsedStorageKey(key: string) {
    return `${this.collapsedStoragePrefix}.${key}`;
  }

}
