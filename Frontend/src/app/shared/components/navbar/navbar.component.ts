import { Component, ChangeDetectionStrategy, Injector } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { appPath } from '../../../path/app-path-const';

type NavSectionKey = 'public' | 'private' | 'admin' | 'superadmin';

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
export class NavbarComponent {
  path = appPath; // 將 appPath 物件賦值給 path 屬性

  collapsed = true;
  readonly sections: NavSection[] = [
    {
      key: 'public',
      items: [
        { labelKey: 'nav.public.home', icon: 'home', route: appPath.home },
        { labelKey: 'nav.public.member', icon: 'groups', route: appPath.member },
        { labelKey: 'nav.public.about', icon: 'info', route: appPath.aboutwebsite },
        { labelKey: 'nav.public.tutorial', icon: 'school', route: appPath.tutorial },
        { labelKey: 'nav.public.update', icon: 'new_releases', route: appPath.update },
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
        { labelKey: 'nav.admin.logs', icon: 'article', route: appPath.home },
        { labelKey: 'nav.admin.announce', icon: 'notifications_active', route: appPath.home },
        { labelKey: 'nav.admin.events', icon: 'event', route: appPath.home },
        { labelKey: 'nav.admin.projects', icon: 'workspaces', route: appPath.home },
        { labelKey: 'nav.admin.member', icon: 'badge', route: appPath.home }
      ]
    },
    {
      key: 'superadmin',
      requires: 'superadmin',
      items: [
        { labelKey: 'nav.superadmin.promote', icon: 'admin_panel_settings', route: appPath.promote },
        { labelKey: 'nav.superadmin.feature', icon: 'extension', route: appPath.home }
      ]
    }
  ];

  constructor(
    private router: Router,
    private injector: Injector,
    private translate: TranslateService
  ) {}

  toggleSidebar() {
    this.collapsed = !this.collapsed;
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

  logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('username');
    this.collapsed = true;
    this.openLogoutSnack();
    this.router.navigate([appPath.login]);
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
