import { Component, ChangeDetectionStrategy } from '@angular/core';

import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { environment } from '../../../../environments/environment';
import { StudioThemeId, ThemeService } from '../../../core/services/theme.service';
import { appPath } from '../../../path/app-path-const';

@Component({
  selector: 'app-setting',
  standalone: false,
  templateUrl: './setting.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './setting.component.css'
})
export class SettingComponent {
  oldPassword = '';
  newPassword = '';
  passwordMessage = '';
  isSuccessMessage = false;
  submitting = false;
  deleteConfirmation = '';
  deleteAccountMessage = '';
  deletingAccount = false;
  
  constructor(
    private http: HttpClient,
    private router: Router,
    private translate: TranslateService,
    public theme: ThemeService
  ) {}

  changePassword() {
    if (this.submitting) {
      return;
    }

    this.submitting = true;
    this.passwordMessage = '';
    this.isSuccessMessage = false;

    this.http.put(`${environment.apiUrl}/changepassword`, {
      old_password: this.oldPassword,
      new_password: this.newPassword
    }).subscribe({
      next: () => {
        this.passwordMessage = this.translate.instant('privateSetting.feedback.passwordSuccess');
        this.isSuccessMessage = true;
        this.oldPassword = '';
        this.newPassword = '';
        this.submitting = false;
      },
      error: (err) => {
        this.passwordMessage = err.error.error || this.translate.instant('privateSetting.feedback.passwordFailure');
        this.isSuccessMessage = false;
        this.submitting = false;
      }
    });
  }

  setSiteTheme(themeId: StudioThemeId) {
    this.theme.setSiteTheme(themeId);
  }

  get canDeleteAccount() {
    return this.deleteConfirmation === 'DELETE' && !this.deletingAccount;
  }

  deleteAccount() {
    if (!this.canDeleteAccount) {
      return;
    }

    this.deletingAccount = true;
    this.deleteAccountMessage = '';

    this.http.request<{ message: string }>('DELETE', `${environment.apiUrl}/me`, {
      body: { confirmation: this.deleteConfirmation }
    }).subscribe({
      next: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('role');
        localStorage.removeItem('username');
        this.router.navigate([appPath.login]);
      },
      error: (err) => {
        this.deleteAccountMessage = err.error?.error || this.translate.instant('privateSetting.danger.feedback.failure');
        this.deletingAccount = false;
      }
    });
  }
}
