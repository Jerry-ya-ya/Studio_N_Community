import { Component, ChangeDetectionStrategy, OnInit } from '@angular/core';
import { CommunityNewsItem, HomeContentService } from '../../../core/services/home-content.service';
import { ThemeService } from '../../../core/services/theme.service';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-home',
  standalone: false,
  templateUrl: './home.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './home.component.css'
})
export class HomeComponent implements OnInit {
  private readonly assetBaseUrl = environment.apiUrl.replace(/\/api\/?$/, '');

  readonly cmenSubtitleKeys = [
    'home.hero.cmen.subtitle.computing',
    'home.hero.cmen.subtitle.mathematics',
    'home.hero.cmen.subtitle.engineering',
    'home.hero.cmen.subtitle.network'
  ];
  readonly edenSubtitleKeys = [
    'home.hero.eden.subtitle.encode',
    'home.hero.eden.subtitle.develop',
    'home.hero.eden.subtitle.enlighten',
    'home.hero.eden.subtitle.nexus'
  ];

  constructor(
    public theme: ThemeService,
    private homeContent: HomeContentService
  ) {}

  ngOnInit() {
    this.homeContent.loadPublicContent().subscribe({
      error: error => console.error('Failed to load homepage news:', error)
    });
  }

  get isNightMode() {
    return this.theme.isNightMode;
  }

  get studioName() {
    return this.isNightMode ? 'EDEN' : 'CMENStudio';
  }

  get studioKickerKey() {
    return this.isNightMode ? 'home.hero.eden.kicker' : 'home.hero.cmen.kicker';
  }

  get studioSubtitleKeys() {
    return this.isNightMode ? this.edenSubtitleKeys : this.cmenSubtitleKeys;
  }

  get studioLogo() {
    return this.isNightMode ? 'icons/eden.png' : 'icons/cmenstudio.png';
  }

  get heroStatusKey() {
    return this.isNightMode ? 'home.hero.eden.status' : 'home.hero.cmen.status';
  }

  get communityNews() {
    return this.homeContent.getNews(this.isNightMode ? 'eden' : 'cmen');
  }

  get communityNewsTitleKey() {
    return this.isNightMode ? 'home.news.edenTitle' : 'home.news.cmenTitle';
  }

  get communityNewsIntroKey() {
    return this.isNightMode ? 'home.news.edenIntro' : 'home.news.cmenIntro';
  }

  getNewsBackgroundUrl(item: CommunityNewsItem) {
    const url = item.backgroundUrl?.trim();
    if (!url) {
      return '';
    }

    if (/^https?:\/\//i.test(url)) {
      return url;
    }

    return `${this.assetBaseUrl}${url.startsWith('/') ? url : `/${url}`}`;
  }

  getNewsBackgroundStyle(item: CommunityNewsItem) {
    const url = this.getNewsBackgroundUrl(item);
    return url
      ? `linear-gradient(180deg, rgba(4, 10, 22, 0.1), rgba(4, 10, 22, 0.76)), url("${url}")`
      : '';
  }
}
