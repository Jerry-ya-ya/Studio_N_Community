import { DOCUMENT } from '@angular/common';
import { Inject, Injectable, OnDestroy } from '@angular/core';

export type StudioThemeId = 'eden' | 'arcade' | 'cyber';

export interface StudioThemeOption {
  id: StudioThemeId;
  labelKey: string;
  descriptionKey: string;
}

@Injectable({
  providedIn: 'root'
})
export class ThemeService implements OnDestroy {
  readonly themeOptions: StudioThemeOption[] = [
    {
      id: 'eden',
      labelKey: 'privateSetting.theme.options.eden.label',
      descriptionKey: 'privateSetting.theme.options.eden.description'
    },
    {
      id: 'arcade',
      labelKey: 'privateSetting.theme.options.arcade.label',
      descriptionKey: 'privateSetting.theme.options.arcade.description'
    },
    {
      id: 'cyber',
      labelKey: 'privateSetting.theme.options.cyber.label',
      descriptionKey: 'privateSetting.theme.options.cyber.description'
    }
  ];

  private readonly cycleSeconds = 300;
  private readonly defaultWorldModeIsNight = true;
  private readonly defaultWorldLocked = true;
  private readonly storageKey = 'studio-theme';
  private timerId: ReturnType<typeof setInterval> | null = null;

  isNightMode = this.defaultWorldModeIsNight;
  isWorldLocked = this.defaultWorldLocked;
  remainingSeconds = this.cycleSeconds;
  activeTheme: StudioThemeId = 'eden';

  constructor(@Inject(DOCUMENT) private document: Document) {
    this.activeTheme = this.readStoredTheme();
    this.syncBodyTheme();
    this.startWorldTimer();
  }

  get nextModeLabel() {
    if (this.isWorldLocked) {
      return this.isNightMode ? 'EDEN LOCK' : 'CMEN LOCK';
    }

    return this.isNightMode ? 'CMEN DAY' : 'EDEN NIGHT';
  }

  get countdownLabel() {
    if (this.isWorldLocked) {
      return 'LOCKED';
    }

    const minutes = Math.floor(this.remainingSeconds / 60).toString().padStart(2, '0');
    const seconds = (this.remainingSeconds % 60).toString().padStart(2, '0');
    return `${minutes}:${seconds}`;
  }

  get lockStateLabel() {
    return this.isWorldLocked ? 'ON' : 'OFF';
  }

  toggleWorldMode() {
    this.setWorldMode(!this.isNightMode);
  }

  setWorldMode(isNightMode: boolean) {
    if (this.isNightMode === isNightMode) {
      return;
    }

    this.isNightMode = isNightMode;
    this.remainingSeconds = this.cycleSeconds;
    this.syncBodyTheme();
  }

  toggleWorldLock() {
    this.isWorldLocked = !this.isWorldLocked;

    if (!this.isWorldLocked) {
      this.remainingSeconds = this.cycleSeconds;
    }
  }

  setSiteTheme(themeId: StudioThemeId) {
    if (this.activeTheme === themeId) {
      return;
    }

    this.activeTheme = themeId;
    localStorage.setItem(this.storageKey, themeId);
    this.syncBodyTheme();
  }

  ngOnDestroy() {
    if (this.timerId) {
      clearInterval(this.timerId);
    }
  }

  private startWorldTimer() {
    if (this.timerId) {
      return;
    }

    this.timerId = setInterval(() => {
      if (this.isWorldLocked) {
        return;
      }

      this.remainingSeconds -= 1;

      if (this.remainingSeconds <= 0) {
        this.toggleWorldMode();
      }
    }, 1000);
  }

  private syncBodyTheme() {
    this.document.body.classList.toggle('eden-night-theme', this.isNightMode);
    this.document.body.classList.toggle('cmen-day-theme', !this.isNightMode);

    for (const theme of this.themeOptions) {
      this.document.body.classList.toggle(`studio-theme-${theme.id}`, this.activeTheme === theme.id);
    }
  }

  private readStoredTheme(): StudioThemeId {
    const storedTheme = localStorage.getItem(this.storageKey);
    return this.themeOptions.some(theme => theme.id === storedTheme) ? storedTheme as StudioThemeId : 'eden';
  }
}
