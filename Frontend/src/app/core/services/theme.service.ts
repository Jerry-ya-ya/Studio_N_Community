import { DOCUMENT } from '@angular/common';
import { Inject, Injectable, OnDestroy } from '@angular/core';

export type StudioThemeId = 'eden' | 'arcade' | 'cyber' | 'onyx' | 'ivory' | 'aurora' | 'ember' | 'mint' | 'royal';

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
    },
    {
      id: 'onyx',
      labelKey: 'privateSetting.theme.options.onyx.label',
      descriptionKey: 'privateSetting.theme.options.onyx.description'
    },
    {
      id: 'ivory',
      labelKey: 'privateSetting.theme.options.ivory.label',
      descriptionKey: 'privateSetting.theme.options.ivory.description'
    },
    {
      id: 'aurora',
      labelKey: 'privateSetting.theme.options.aurora.label',
      descriptionKey: 'privateSetting.theme.options.aurora.description'
    },
    {
      id: 'ember',
      labelKey: 'privateSetting.theme.options.ember.label',
      descriptionKey: 'privateSetting.theme.options.ember.description'
    },
    {
      id: 'mint',
      labelKey: 'privateSetting.theme.options.mint.label',
      descriptionKey: 'privateSetting.theme.options.mint.description'
    },
    {
      id: 'royal',
      labelKey: 'privateSetting.theme.options.royal.label',
      descriptionKey: 'privateSetting.theme.options.royal.description'
    }
  ];

  private readonly cycleSeconds = 300;
  private readonly defaultWorldModeIsNight = true;
  private readonly defaultWorldLocked = true;
  private readonly storageKey = 'studio-theme';
  private readonly edenBrowserTitle = 'EDEN';
  private readonly cmenBrowserTitle = 'CMENStudio';
  private readonly edenBrowserIcon = 'icons/eden.png';
  private readonly cmenBrowserIcon = 'icons/cmenstudio.png';
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
    this.syncBrowserTitle();

    for (const theme of this.themeOptions) {
      this.document.body.classList.toggle(`studio-theme-${theme.id}`, this.activeTheme === theme.id);
    }
  }

  private syncBrowserTitle() {
    const title = this.isNightMode ? this.edenBrowserTitle : this.cmenBrowserTitle;
    this.document.title = title;
    this.syncBrowserIcon();

    const appleTitle = this.document.querySelector<HTMLMetaElement>('meta[name="apple-mobile-web-app-title"]');
    if (appleTitle) {
      appleTitle.content = title;
    }
  }

  private syncBrowserIcon() {
    const icon = this.isNightMode ? this.edenBrowserIcon : this.cmenBrowserIcon;
    this.setLinkHref('icon', icon);
    this.setLinkHref('apple-touch-icon', icon);
  }

  private setLinkHref(rel: string, href: string) {
    let link = this.document.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`);

    if (!link) {
      link = this.document.createElement('link');
      link.rel = rel;
      this.document.head.appendChild(link);
    }

    link.href = href;
    if (rel === 'icon') {
      link.type = 'image/png';
    }
  }

  private readStoredTheme(): StudioThemeId {
    const storedTheme = localStorage.getItem(this.storageKey);
    return this.themeOptions.some(theme => theme.id === storedTheme) ? storedTheme as StudioThemeId : 'eden';
  }
}
