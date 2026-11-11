import { Component, ChangeDetectionStrategy, OnInit } from '@angular/core';
import { CommunityNewsItem, HomeContentService } from '../../../core/services/home-content.service';
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

  readonly studioName = 'EDEN';
  readonly studioLogo = 'icons/eden.png';
  readonly studioSubtitleKeys = [
    'home.hero.eden.subtitle.encode',
    'home.hero.eden.subtitle.develop',
    'home.hero.eden.subtitle.enlighten',
    'home.hero.eden.subtitle.nexus'
  ];

  constructor(
    private homeContent: HomeContentService
  ) {}

  ngOnInit() {
    this.homeContent.loadPublicContent().subscribe({
      error: error => console.error('Failed to load homepage news:', error)
    });
  }

  get communityNews() {
    return this.homeContent.getNews('eden');
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
