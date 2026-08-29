import { Component, ChangeDetectionStrategy, EventEmitter, Injector, OnInit, Output } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { appPath } from '../../../path/app-path-const';
import { ThemeService } from '../../../core/services/theme.service';
import { ApiService } from '../../../core/services/api.service';

type NavSectionKey = 'public' | 'private' | 'admin' | 'superadmin';
const NAV_COLLAPSED_STORAGE_KEY = 'navbarCollapsed';

interface NavItem {
  labelKey: string;
  icon: string;
  route?: string;
  action?: 'logout';
}

interface NavSection {
  key: NavSectionKey;
  items: NavItem[];
  requires?: 'loggedIn' | 'admin' | 'superadmin';
}

@Component({
  selector: 'app-navbar',
  standalone: false,
  templateUrl: './navbar.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './navbar.component.css'
})
export class NavbarComponent implements OnInit {
  path = appPath; // 將 appPath 物件賦值給 path 屬性

  @Output() collapsedChange = new EventEmitter<boolean>();

  collapsed = localStorage.getItem(NAV_COLLAPSED_STORAGE_KEY) !== 'false';
  readonly sections: NavSection[] = [
    {
      key: 'public',
      items: [
        { labelKey: 'nav.public.home', icon: 'home', route: appPath.home },
        { labelKey: 'nav.public.member', icon: 'groups', route: appPath.member },
        { labelKey: 'nav.public.about', icon: 'info', route: appPath.aboutwebsite },
        { labelKey: 'nav.public.tutorial', icon: 'school', route: appPath.tutorial },
        { labelKey: 'nav.public.update', icon: 'new_releases', route: appPath.update },
        { labelKey: 'nav.public.activities', icon: 'local_activity', route: appPath.publicActivities },
        { labelKey: 'nav.public.register', icon: 'person_add', route: appPath.register },
        { labelKey: 'nav.public.login', icon: 'login', route: appPath.login }
      ]
    },
    {
      key: 'private',
      requires: 'loggedIn',
      items: [
        { labelKey: 'nav.private.home', icon: 'dashboard', route: appPath.userhome },
        { labelKey: 'nav.private.postWall', icon: 'forum', route: appPath.post },
        { labelKey: 'nav.private.square', icon: 'grid_view', route: appPath.square },
        { labelKey: 'nav.private.recruit', icon: 'campaign', route: appPath.projectRecruitment },
        { labelKey: 'nav.private.friend', icon: 'diversity_3', route: appPath.friend },
        { labelKey: 'nav.private.todo', icon: 'task_alt', route: appPath.todo },
        { labelKey: 'nav.private.checkIn', icon: 'redeem', route: appPath.checkIn },
        { labelKey: 'nav.private.schedule', icon: 'calendar_month', route: appPath.schedule },
        { labelKey: 'nav.private.activities', icon: 'celebration', route: appPath.privateActivities },
        { labelKey: 'nav.private.setting', icon: 'settings', route: appPath.setting },
        { labelKey: 'nav.private.profile', icon: 'account_circle', route: appPath.profile },
        { labelKey: 'nav.private.crawler', icon: 'travel_explore', route: appPath.crawler },
        { labelKey: 'nav.private.logout', icon: 'logout', action: 'logout' }
      ]
    },
    {
      key: 'admin',
      requires: 'admin',
      items: [
        { labelKey: 'nav.admin.user', icon: 'manage_accounts', route: appPath.home },
        { labelKey: 'nav.admin.content', icon: 'edit_note', route: appPath.content },
        { labelKey: 'nav.admin.logs', icon: 'article', route: appPath.adminLogs },
        { labelKey: 'nav.admin.announce', icon: 'notifications_active', route: appPath.home },
        { labelKey: 'nav.admin.events', icon: 'event', route: appPath.activity },
        { labelKey: 'nav.admin.projects', icon: 'workspaces', route: appPath.projects },
        { labelKey: 'nav.admin.member', icon: 'badge', route: appPath.home }
      ]
    },
    {
      key: 'superadmin',
      requires: 'superadmin',
      items: [
        { labelKey: 'nav.superadmin.promote', icon: 'admin_panel_settings', route: appPath.promote },
        { labelKey: 'nav.superadmin.logs', icon: 'receipt_long', route: appPath.superadminLogs },
        { labelKey: 'nav.superadmin.feature', icon: 'extension', route: appPath.home }
      ]
    }
  ];

  constructor(
    private router: Router,
    private injector: Injector,
    private translate: TranslateService,
    public theme: ThemeService,
    private apiService: ApiService
  ) {}

  ngOnInit() {
    this.collapsedChange.emit(this.collapsed);
  }

  toggleSidebar() {
    this.collapsed = !this.collapsed;
    this.saveCollapsedState();
    this.collapsedChange.emit(this.collapsed);
  }

  isSectionVisible(section: NavSection) {
    if (section.requires === 'loggedIn') {
      return this.isLoggedIn();
    }
    if (section.requires === 'admin') {
      return this.isAdmin();
    }
    if (section.requires === 'superadmin') {
      return this.isSuperadmin();
    }

    return true;
  }

  get brandName() {
    return this.theme.isNightMode ? 'EDEN' : 'CMENStudio';
  }

  get homeEntryPath() {
    return this.isLoggedIn() ? appPath.userhome : appPath.home;
  }

  logout() {
    this.apiService.delete('/refresh').subscribe({ error: () => undefined });
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('role');
    localStorage.removeItem('username');
    this.collapsed = true;
    this.saveCollapsedState();
    this.collapsedChange.emit(this.collapsed);
    this.openLogoutSnack();
    this.router.navigate([appPath.login]);
  }

  private saveCollapsedState() {
    localStorage.setItem(NAV_COLLAPSED_STORAGE_KEY, String(this.collapsed));
  }

  private async openLogoutSnack() {
    const { MatSnackBar } = await import('@angular/material/snack-bar');
    const snackBar = this.injector.get(MatSnackBar);

    snackBar.open(
      this.translate.instant('login.feedback.logoutSuccess'),
      this.translate.instant('login.feedback.dismiss'),
      {
        duration: 3000,
        horizontalPosition: 'right',
        verticalPosition: 'top',
        panelClass: ['studio-snackbar', 'studio-snackbar-success']
      }
    );
  }

  isLoggedIn() {
    return !!localStorage.getItem('token');
  }

  isAdmin() {
    return localStorage.getItem('role') === 'admin' || localStorage.getItem('role') === 'superadmin';
  }

  isSuperadmin() {
    return localStorage.getItem('role') === 'superadmin';
  }
}
