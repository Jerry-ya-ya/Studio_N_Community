import { Component, ChangeDetectionStrategy } from '@angular/core';
import { appPath } from './path/app-path-const';
import { TranslateService } from '@ngx-translate/core';
import { AuthSessionService } from './core/services/auth-session.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  standalone: false,
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'jackandbeanstalks';
  path = appPath;
  readonly languages = [
    { code: 'zh-TW', label: '繁中', name: 'Traditional Chinese' },
    { code: 'en', label: 'EN', name: 'English' },
    { code: 'ja', label: 'JP', name: 'Japanese' },
    { code: 'ko', label: 'KR', name: 'Korean' }
  ];
  currentLanguage = localStorage.getItem('language') || 'zh-TW';
  languageMenuOpen = false;

  constructor(
    private translate: TranslateService,
    private authSession: AuthSessionService
  ) {
    this.translate.use(this.currentLanguage);
  }

  switchLanguage(language: string) {
    this.currentLanguage = language;
    localStorage.setItem('language', language);
    this.translate.use(language);
    this.languageMenuOpen = false;
  }

  toggleLanguageMenu() {
    this.languageMenuOpen = !this.languageMenuOpen;
  }

  get currentLanguageLabel() {
    return this.languages.find(language => language.code === this.currentLanguage)?.label || '繁中';
  }

  get isLoggedIn() {
    return this.authSession.isAuthenticated;
  }

  get topActionPath() {
    return this.isLoggedIn ? appPath.todo : appPath.login;
  }

  get topActionLabelKey() {
    return this.isLoggedIn ? 'nav.private.todo' : 'nav.public.login';
  }

}
