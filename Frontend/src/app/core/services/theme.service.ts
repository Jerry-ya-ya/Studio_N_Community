import { DOCUMENT } from '@angular/common';
import { Inject, Injectable, OnDestroy } from '@angular/core';

export type StudioThemeId = 'eden' | 'arcade' | 'cyber' | 'onyx' | 'ivory' | 'aurora' | 'ember' | 'mint' | 'royal';

export interface StudioThemeOption {
  id: StudioThemeId;
  labelKey: string;
  descriptionKey: string;
}

interface StudioThemeTokens {
  bg: string;
  panel: string;
  panelStrong: string;
  line: string;
  text: string;
  muted: string;
  accent: string;
  warm: string;
  danger: string;
  success: string;
}

const themeTokens: Record<StudioThemeId, StudioThemeTokens> = {
  eden: {
    bg: '#020503',
    panel: 'rgba(3, 14, 10, 0.82)',
    panelStrong: 'rgba(5, 18, 12, 0.94)',
    line: 'rgba(94, 255, 126, 0.28)',
    text: '#effff2',
    muted: '#a7cdb2',
    accent: '#65ff82',
    warm: '#d8ff62',
    danger: '#ff6f7d',
    success: '#20d889',
  },
  arcade: {
    bg: '#100716',
    panel: 'rgba(28, 8, 30, 0.84)',
    panelStrong: 'rgba(22, 5, 28, 0.94)',
    line: 'rgba(255, 79, 216, 0.32)',
    text: '#fff1fb',
    muted: '#f3bfe9',
    accent: '#ff4fd8',
    warm: '#ffd166',
    danger: '#ff6f91',
    success: '#53ecff',
  },
  cyber: {
    bg: '#020816',
    panel: 'rgba(3, 12, 30, 0.84)',
    panelStrong: 'rgba(2, 8, 22, 0.94)',
    line: 'rgba(83, 236, 255, 0.32)',
    text: '#eefbff',
    muted: '#a7d8e2',
    accent: '#53ecff',
    warm: '#9bff7a',
    danger: '#ff6f7d',
    success: '#9bff7a',
  },
  onyx: {
    bg: '#030304',
    panel: 'rgba(12, 12, 14, 0.86)',
    panelStrong: 'rgba(5, 5, 7, 0.96)',
    line: 'rgba(224, 232, 240, 0.18)',
    text: '#f7f7f2',
    muted: '#b7bbc3',
    accent: '#8ee6ff',
    warm: '#ffd36a',
    danger: '#ff6f7d',
    success: '#80f0b5',
  },
  ivory: {
    bg: '#f4f1e8',
    panel: 'rgba(255, 252, 244, 0.86)',
    panelStrong: 'rgba(255, 255, 250, 0.96)',
    line: 'rgba(36, 47, 59, 0.18)',
    text: '#18212c',
    muted: '#536170',
    accent: '#156f8f',
    warm: '#c64f38',
    danger: '#c73b52',
    success: '#287a55',
  },
  aurora: {
    bg: '#061116',
    panel: 'rgba(7, 22, 30, 0.84)',
    panelStrong: 'rgba(4, 15, 22, 0.94)',
    line: 'rgba(135, 255, 220, 0.28)',
    text: '#effffb',
    muted: '#a8d6d0',
    accent: '#7dffd5',
    warm: '#cfa7ff',
    danger: '#ff7a93',
    success: '#8cff9e',
  },
  ember: {
    bg: '#120806',
    panel: 'rgba(31, 12, 8, 0.84)',
    panelStrong: 'rgba(22, 7, 5, 0.94)',
    line: 'rgba(255, 149, 74, 0.3)',
    text: '#fff5ea',
    muted: '#e2b99d',
    accent: '#ff934f',
    warm: '#ffe071',
    danger: '#ff6370',
    success: '#8cff9e',
  },
  mint: {
    bg: '#eaf7f0',
    panel: 'rgba(247, 255, 250, 0.86)',
    panelStrong: 'rgba(252, 255, 253, 0.96)',
    line: 'rgba(25, 117, 89, 0.2)',
    text: '#13261f',
    muted: '#4f6f63',
    accent: '#168961',
    warm: '#5367d8',
    danger: '#c34c65',
    success: '#1f9d68',
  },
  royal: {
    bg: '#080718',
    panel: 'rgba(16, 13, 42, 0.84)',
    panelStrong: 'rgba(10, 8, 30, 0.94)',
    line: 'rgba(169, 136, 255, 0.3)',
    text: '#f6f1ff',
    muted: '#c7bae8',
    accent: '#a988ff',
    warm: '#f5ce65',
    danger: '#ff7a93',
    success: '#7dffd5',
  },
};

const themePageBackgrounds: Record<StudioThemeId, string> = {
  eden: `
    radial-gradient(circle at 18% 18%, rgba(94, 255, 126, 0.14), transparent 28%),
    radial-gradient(circle at 82% 22%, rgba(40, 216, 137, 0.12), transparent 24%),
    linear-gradient(135deg, #020503 0%, #08150e 54%, #030907 100%)
  `,
  arcade: `
    radial-gradient(circle at 16% 16%, rgba(255, 79, 216, 0.17), transparent 28%),
    radial-gradient(circle at 84% 22%, rgba(83, 236, 255, 0.13), transparent 24%),
    linear-gradient(135deg, #100716 0%, #220d2b 54%, #070a1d 100%)
  `,
  cyber: `
    radial-gradient(circle at 18% 18%, rgba(83, 236, 255, 0.15), transparent 28%),
    radial-gradient(circle at 82% 22%, rgba(118, 91, 255, 0.13), transparent 24%),
    linear-gradient(135deg, #020816 0%, #061c30 54%, #030714 100%)
  `,
  onyx: `
    radial-gradient(circle at 18% 18%, rgba(142, 230, 255, 0.12), transparent 26%),
    radial-gradient(circle at 82% 20%, rgba(255, 211, 106, 0.1), transparent 22%),
    linear-gradient(135deg, #030304 0%, #101014 54%, #050509 100%)
  `,
  ivory: `
    radial-gradient(circle at 16% 18%, rgba(21, 111, 143, 0.13), transparent 28%),
    radial-gradient(circle at 84% 18%, rgba(198, 79, 56, 0.1), transparent 24%),
    linear-gradient(135deg, #f8f6ef 0%, #ebe7dc 54%, #f6f3ea 100%)
  `,
  aurora: `
    radial-gradient(circle at 18% 18%, rgba(125, 255, 213, 0.16), transparent 28%),
    radial-gradient(circle at 80% 22%, rgba(207, 167, 255, 0.14), transparent 24%),
    linear-gradient(135deg, #061116 0%, #0b2630 54%, #110a24 100%)
  `,
  ember: `
    radial-gradient(circle at 16% 18%, rgba(255, 147, 79, 0.16), transparent 28%),
    radial-gradient(circle at 84% 20%, rgba(255, 224, 113, 0.12), transparent 23%),
    linear-gradient(135deg, #120806 0%, #2a1109 54%, #080b10 100%)
  `,
  mint: `
    radial-gradient(circle at 18% 18%, rgba(22, 137, 97, 0.13), transparent 28%),
    radial-gradient(circle at 82% 20%, rgba(83, 103, 216, 0.1), transparent 24%),
    linear-gradient(135deg, #f5fff9 0%, #e3f3ed 54%, #eef4ff 100%)
  `,
  royal: `
    radial-gradient(circle at 18% 18%, rgba(169, 136, 255, 0.16), transparent 28%),
    radial-gradient(circle at 84% 20%, rgba(245, 206, 101, 0.12), transparent 24%),
    linear-gradient(135deg, #080718 0%, #171038 54%, #06030e 100%)
  `,
};

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

    this.syncSelectedThemeTokens();
  }

  private syncSelectedThemeTokens() {
    const theme = themeTokens[this.activeTheme];
    const pageBackground = themePageBackgrounds[this.activeTheme].trim();
    const surfaceBackground = `
      linear-gradient(135deg, rgba(255, 255, 255, 0.07), transparent 34%),
      color-mix(in srgb, ${theme.panelStrong} 92%, #000 8%)
    `.trim();

    this.document.body.style.setProperty('--studio-bg', theme.bg);
    this.document.body.style.setProperty('--studio-panel', theme.panel);
    this.document.body.style.setProperty('--studio-panel-strong', theme.panelStrong);
    this.document.body.style.setProperty('--studio-line', theme.line);
    this.document.body.style.setProperty('--studio-text', theme.text);
    this.document.body.style.setProperty('--studio-muted', theme.muted);
    this.document.body.style.setProperty('--studio-accent', theme.accent);
    this.document.body.style.setProperty('--studio-warm', theme.warm);
    this.document.body.style.setProperty('--studio-danger', theme.danger);
    this.document.body.style.setProperty('--studio-success', theme.success);
    this.document.body.style.setProperty('--theme-page-bg', pageBackground);
    this.document.body.style.setProperty('--studio-page-bg', pageBackground);
    this.document.body.style.setProperty('--studio-shell-bg', pageBackground);
    this.document.body.style.setProperty('--studio-surface-bg', surfaceBackground);
    this.document.body.style.setProperty('--theme-bg', theme.bg);
    this.document.body.style.setProperty('--theme-surface', theme.panelStrong);
    this.document.body.style.setProperty('--theme-card', theme.panel);
    this.document.body.style.setProperty('--theme-border', theme.line);
    this.document.body.style.setProperty('--theme-text', theme.text);
    this.document.body.style.setProperty('--theme-heading', theme.text);
    this.document.body.style.setProperty('--theme-muted', theme.muted);
    this.document.body.style.setProperty('--theme-primary', theme.accent);
    this.document.body.style.setProperty('--theme-danger', theme.danger);
    this.document.body.style.setProperty('--theme-success', theme.success);
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
