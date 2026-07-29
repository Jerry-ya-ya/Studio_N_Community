import { Injectable } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { ApiService } from './api.service';

export interface CommunityNewsItem {
  id?: number | null;
  theme?: keyof HomeNewsContent;
  title: string;
  summary: string;
  tag: string;
  backgroundUrl?: string | null;
  sort_order?: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface HomeNewsContent {
  cmen: CommunityNewsItem[];
  eden: CommunityNewsItem[];
}

export const defaultHomeNewsContent: HomeNewsContent = {
  cmen: [
    {
      title: 'Prototype Lab Opens',
      summary: 'A small corner for gameplay sketches, tiny tools, and strange experiments.',
      tag: 'Studio'
    },
    {
      title: 'Player Notes Wanted',
      summary: 'Collecting first impressions before the next round of game-facing polish.',
      tag: 'Community'
    },
    {
      title: 'Devlog Queue',
      summary: 'Future posts will track builds, experiments, and useful lessons from production.',
      tag: 'Devlog'
    }
  ],
  eden: [
    {
      title: 'Knowledge Node Online',
      summary: 'EDEN prepares a shared space for questions, references, and learning trails.',
      tag: 'Network'
    },
    {
      title: 'Learning Routes Drafted',
      summary: 'Encode, Develop, Enlighten, and Nexus will shape the first content channels.',
      tag: 'Roadmap'
    },
    {
      title: 'Admin News Tools Planned',
      summary: 'Community news cards are placeholders until editable publishing is unlocked.',
      tag: 'System'
    }
  ]
};

@Injectable({
  providedIn: 'root'
})
export class HomeContentService {
  private content = this.clone(defaultHomeNewsContent);

  constructor(private apiService: ApiService) {}

  getContentSnapshot(): HomeNewsContent {
    return this.clone(this.content);
  }

  getNews(theme: keyof HomeNewsContent): CommunityNewsItem[] {
    return this.content[theme];
  }

  loadPublicContent(): Observable<HomeNewsContent> {
    return this.apiService.get<HomeNewsContent>('/content/home-news').pipe(
      tap(content => this.content = this.normalizeContent(content))
    );
  }

  loadAdminContent(): Observable<HomeNewsContent> {
    return this.apiService.get<HomeNewsContent>('/admin/content/home-news', this.apiService.createAuthHeaders()).pipe(
      tap(content => this.content = this.normalizeContent(content))
    );
  }

  saveAdminContent(content: HomeNewsContent): Observable<HomeNewsContent> {
    return this.apiService.put<HomeNewsContent>(
      '/admin/content/home-news',
      content,
      this.apiService.createAuthHeaders()
    ).pipe(
      tap(saved => this.content = this.normalizeContent(saved))
    );
  }

  uploadNewsBackground(itemId: number, file: File): Observable<CommunityNewsItem> {
    const formData = new FormData();
    formData.append('file', file);

    return this.apiService.post<CommunityNewsItem>(
      `/admin/content/home-news/items/${itemId}/background`,
      formData,
      this.apiService.createAuthHeaders()
    );
  }

  getDefaultContent(): HomeNewsContent {
    return this.clone(defaultHomeNewsContent);
  }

  private normalizeContent(content: Partial<HomeNewsContent> | null | undefined): HomeNewsContent {
    return {
      cmen: this.normalizeNews(content?.cmen, defaultHomeNewsContent.cmen),
      eden: this.normalizeNews(content?.eden, defaultHomeNewsContent.eden)
    };
  }

  private normalizeNews(items: unknown, fallback: CommunityNewsItem[]) {
    if (!Array.isArray(items)) {
      return this.clone(fallback);
    }

    return items.map(item => {
      const newsItem = item as Partial<CommunityNewsItem>;
      return {
        id: newsItem.id ?? null,
        theme: newsItem.theme,
        title: String(newsItem.title ?? ''),
        summary: String(newsItem.summary ?? ''),
        tag: String(newsItem.tag ?? ''),
        backgroundUrl: newsItem.backgroundUrl ?? null,
        sort_order: newsItem.sort_order,
        created_at: newsItem.created_at ?? null,
        updated_at: newsItem.updated_at ?? null
      };
    }).filter(item => item.title.trim() || item.summary.trim() || item.tag.trim());
  }

  private clone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
  }
}
