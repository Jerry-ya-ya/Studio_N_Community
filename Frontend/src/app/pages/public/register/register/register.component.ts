import { Component, ChangeDetectionStrategy } from '@angular/core';
import { ApiService } from '../../../../core/services/api.service';
import { appPath } from '../../../../path/app-path-const';

@Component({
  selector: 'app-register',
  standalone: false,
  templateUrl: './register.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './register.component.css'
})
export class RegisterComponent {
  path = appPath;
  username = '';
  password = '';
  email = '';
  nickname = '';
  error = '';
  successMessage = '';
  successMessageKey = '';
  submitting = false;
  
  constructor(private apiService: ApiService) {}

  get registerAction() {
    return `${this.apiService.getCurrentApiUrl()}/register`;
  }

  private storeBrowserCredential(displayName: string) {
    if (!this.username || !this.password) {
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

  register() {
    if (this.submitting) {
      return;
    }

    this.submitting = true;
    this.error = '';
    this.successMessage = '';
    this.successMessageKey = '';

    this.apiService.post<any>('/register', {
      username: this.username,
      password: this.password,
      email: this.email,
    }).subscribe({
      next: res => {
        this.storeBrowserCredential(res.username || this.username);
        this.successMessageKey = 'register.feedback.success';
        this.username = '';
        this.password = '';
        this.email = '';
        this.error = '';
        this.submitting = false;
      },
      error: err => {
        this.error = err.error.error || 'register.feedback.failure';
        this.submitting = false;
      }
    });
  }

  get errorIsTranslationKey() {
    return this.error.startsWith('register.');
  }
}
