import { Component, OnInit } from '@angular/core';
import { timeout } from 'rxjs/operators';
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
export class LogsComponent implements OnInit {
  registerItems: AuditLogItem[] = [];
  registerLoading = false;
  registerError = '';
  registerSource = '';

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

  constructor(private auditLogService: AuditLogService) {}

  ngOnInit() {
    this.loadRegisterLogs();
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

  loadRegisterLogs() {
    this.registerLoading = true;
    this.registerError = '';

    this.auditLogService.getRegisterLogs().pipe(timeout(10000)).subscribe({
      next: response => {
        this.registerItems = Array.isArray(response.items) ? response.items : [];
        this.registerSource = response.path ? `${response.path} / ${response.count ?? this.registerItems.length} records` : '';
        this.registerLoading = false;
        this.registerError = '';
      },
      error: () => {
        this.registerItems = [];
        this.registerSource = '';
        this.registerLoading = false;
        this.registerError = 'Unable to load register logs.';
      }
    });
  }
}
