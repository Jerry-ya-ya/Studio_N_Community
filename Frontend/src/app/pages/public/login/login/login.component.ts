import { Component, ChangeDetectionStrategy } from '@angular/core';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';

import { ApiService } from '../../../../core/services/api.service';
import { appPath } from '../../../../path/app-path-const';

@Component({
  selector: 'app-login',
  standalone: false,
  templateUrl: './login.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './login.component.css'
})
export class LoginComponent {
  path = appPath; // 將 appPath 物件賦值給 path 屬性
  
  username = '';
  password = '';
  role = '';
  rememberLogin = true;

  error = '';
  submitting = false;
  
  constructor(
    private apiService: ApiService,
    private router: Router,
    private snackBar: MatSnackBar,
    private translate: TranslateService
  ) {}

  get loginAction() {
    return `${this.apiService.getCurrentApiUrl()}/login`;
  }

  login() {
    if (this.submitting) {
      return;
    }

    this.submitting = true;
    this.error = '';

    this.apiService.post<any>('/login', {
      username: this.username,
      password: this.password,
    }).subscribe({
      next: res => {
        localStorage.setItem('token', res.access_token);
        localStorage.setItem('username', res.username);
        localStorage.setItem('role', res.role);
        this.storeBrowserCredential(res.username || this.username);
        this.openLoginSnack('login.feedback.success', 'studio-snackbar-success');
        this.router.navigate([appPath.userhome]);
      },
      error: () => {
        this.error = 'login.feedback.failure';
        this.openLoginSnack('login.feedback.failure', 'studio-snackbar-error');
        this.submitting = false;
      }
    });
  }

  private openLoginSnack(messageKey: string, panelClass: string) {
    this.snackBar.open(
      this.translate.instant(messageKey),
      this.translate.instant('login.feedback.dismiss'),
      {
        duration: 3000,
        horizontalPosition: 'right',
        verticalPosition: 'top',
        panelClass: ['studio-snackbar', panelClass]
      }
    );
  }

  private storeBrowserCredential(displayName: string) {
    if (!this.rememberLogin || !this.username || !this.password) {
      return;
    }

    const credentialWindow = window as Window & {
      PasswordCredential?: new (data: { id: string; name?: string; password: string }) => Credential;
    };

    if (!credentialWindow.PasswordCredential || !navigator.credentials?.store) {
      return;
    }

    const credential = new credentialWindow.PasswordCredential({
      id: this.username,
      name: displayName,
      password: this.password
    });

    navigator.credentials.store(credential).catch(() => undefined);
  }
}
