import { Component, ChangeDetectionStrategy } from '@angular/core';
import { appPath } from './path/app-path-const';
import { ThemeService } from './core/services/theme.service';
import { TranslateService } from '@ngx-translate/core';

const NAV_COLLAPSED_STORAGE_KEY = 'navbarCollapsed';

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
  navCollapsed = localStorage.getItem(NAV_COLLAPSED_STORAGE_KEY) !== 'false';

  constructor(
    public theme: ThemeService,
    private translate: TranslateService
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
    return !!localStorage.getItem('token');
  }

  get topActionPath() {
    return this.isLoggedIn ? appPath.todo : appPath.login;
  }

  get topActionLabelKey() {
    return this.isLoggedIn ? 'nav.private.todo' : 'nav.public.login';
  }

  get worldLogoSrc() {
    return this.theme.isNightMode ? 'icons/eden.png' : 'icons/cmenstudio.png';
  }

  get worldLogoName() {
    return this.theme.isNightMode ? 'EDEN' : 'CMEN';
  }

  get worldLogoAriaKey() {
    return this.theme.isNightMode ? 'world.aria.switchToDay' : 'world.aria.switchToNight';
  }

  get worldCycleAriaKey() {
    return this.theme.isWorldLocked ? 'world.cycle.aria.enable' : 'world.cycle.aria.disable';
  }

  get worldCycleStateKey() {
    return this.theme.isWorldLocked ? 'world.lock.off' : 'world.lock.on';
  }
}
