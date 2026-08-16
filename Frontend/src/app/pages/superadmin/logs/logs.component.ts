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
  collapsedGroups: Record<string, boolean> = {};
  private destroy$ = new Subject<void>();
  private refreshRegisterLogs$ = new Subject<void>();
  private readonly collapsedStoragePrefix = 'superadmin.logs.collapsed';

  sections: AuditLogSection[] = [
    {
      title: 'Private',
      eyebrow: 'Member Activity',
      description: 'User-facing records for account creation, project publishing, and sign-in activity.',
      groups: [
        {
          title: 'Register Log',
          description: 'Tracks who registered a new account.',
          accent: 'var(--studio-success)',
          logs: []
        },
        {
          title: 'Project Log',
          description: 'Tracks who created a project recruitment.',
          accent: 'var(--studio-accent)',
          logs: [
            { actor: 'Project leader', action: 'created project', target: 'Eden website', time: 'Pending API', status: 'pending' },
            { actor: 'Team lead', action: 'opened recruitment', target: 'Game studio taskforce', time: 'Pending API', status: 'notice' }
          ]
        },
        {
          title: 'Sign In Log',
          description: 'Tracks successful sign-in activity.',
          accent: 'var(--studio-warm)',
          logs: [
            { actor: 'Jerry', action: 'signed in', target: 'Private home', time: 'Pending API', status: 'success' },
            { actor: 'Member', action: 'refreshed session', target: 'Access token', time: 'Pending API', status: 'notice' }
          ]
        }
      ]
    },
    {
      title: 'Admin',
      eyebrow: 'Management Activity',
      description: 'Administrative records for homepage content and news changes.',
      groups: [
        {
          title: 'Content Log',
          description: 'Tracks who modified public home content.',
          accent: 'var(--studio-danger)',
          logs: [
            { actor: 'Admin', action: 'updated content', target: 'Home news card', time: 'Pending API', status: 'pending' },
            { actor: 'Admin', action: 'changed layout copy', target: 'CMENStudio home', time: 'Pending API', status: 'notice' }
          ]
        },
        {
          title: 'News Log',
          description: 'Tracks who modified news content or background assets.',
          accent: 'var(--studio-accent)',
          logs: [
            { actor: 'Admin', action: 'uploaded background', target: 'Home news image', time: 'Pending API', status: 'pending' },
            { actor: 'Admin', action: 'edited summary', target: 'EDEN news item', time: 'Pending API', status: 'notice' }
          ]
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
    this.initializeRegisterLogStream();
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
  }

  isRegisterGroup(group: AuditLogGroup) {
    return group.title === 'Register Log';
  }

  getGroupLogs(group: AuditLogGroup) {
    return this.isRegisterGroup(group) ? this.registerItems : group.logs;
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

  loadRegisterLogs() {
    this.refreshRegisterLogs$.next();
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
