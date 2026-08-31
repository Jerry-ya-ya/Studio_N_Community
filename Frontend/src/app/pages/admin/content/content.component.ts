import { Component, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import { CommunityNewsItem, HomeContentService, HomeNewsContent } from '../../../core/services/home-content.service';
import { MemberContentItem, MemberContentService } from '../../../core/services/member-content.service';
import { environment } from '../../../../environments/environment';

type ContentSection = 'home-news' | 'member' | 'tutorial' | 'about' | 'system';

@Component({
  selector: 'app-content',
  standalone: false,
  templateUrl: './content.component.html',
  styleUrl: './content.component.css',
})
export class ContentComponent implements OnInit {
  activeSection: ContentSection = 'home-news';
  activeTheme: keyof HomeNewsContent = 'cmen';
  savedMessage = '';
  errorMessage = '';
  loadingHomeContent = false;
  loadingMemberContent = false;
  saving = false;

  readonly sections: { key: ContentSection; labelKey: string; hintKey: string; disabled?: boolean }[] = [
    { key: 'home-news', labelKey: 'adminContent.sections.homeNews.label', hintKey: 'adminContent.sections.homeNews.hint' },
    { key: 'member', labelKey: 'adminContent.sections.member.label', hintKey: 'adminContent.sections.member.hint' },
    { key: 'tutorial', labelKey: 'adminContent.sections.tutorial.label', hintKey: 'adminContent.sections.tutorial.hint', disabled: true },
    { key: 'about', labelKey: 'adminContent.sections.about.label', hintKey: 'adminContent.sections.about.hint', disabled: true },
    { key: 'system', labelKey: 'adminContent.sections.system.label', hintKey: 'adminContent.sections.system.hint', disabled: true }
  ];

  content: HomeNewsContent;
  members: MemberContentItem[];
  uploadingBackground: Record<number, boolean> = {};
  private syncingMemberScroll = false;
  private memberScrollFrame: number | null = null;
  private readonly assetBaseUrl = environment.apiUrl.replace(/\/api\/?$/, '');

  constructor(
    private homeContent: HomeContentService,
    private memberContent: MemberContentService,
    private translate: TranslateService
  ) {
    this.content = this.homeContent.getContentSnapshot();
    this.members = this.memberContent.getSnapshot();
  }

  ngOnInit() {
    this.loadingHomeContent = true;
    this.homeContent.loadAdminContent().pipe(
      finalize(() => this.loadingHomeContent = false)
    ).subscribe({
      next: content => {
        this.content = content;
      },
      error: error => {
        this.errorMessage = error?.error?.error || this.translate.instant('adminContent.feedback.loadFailure');
      }
    });

    this.loadingMemberContent = true;
    this.memberContent.loadAdminContent().pipe(
      finalize(() => this.loadingMemberContent = false)
    ).subscribe({
      next: members => {
        this.members = members;
      },
      error: error => {
        this.errorMessage = error?.error?.error || this.translate.instant('adminContent.feedback.loadMemberFailure');
      }
    });
  }

  get activeNews(): CommunityNewsItem[] {
    return this.content[this.activeTheme];
  }

  setSection(section: ContentSection) {
    const target = this.sections.find(item => item.key === section);
    if (target?.disabled) {
      return;
    }

    this.activeSection = section;
    this.savedMessage = '';
    this.errorMessage = '';
  }

  setTheme(theme: keyof HomeNewsContent) {
    this.activeTheme = theme;
    this.savedMessage = '';
  }

  addNewsItem() {
    this.activeNews.push({
      title: this.translate.instant('adminContent.defaults.newTitle'),
      summary: this.translate.instant('adminContent.defaults.newSummary'),
      tag: this.translate.instant('adminContent.defaults.newTag')
    });
    this.savedMessage = '';
  }

  removeNewsItem(index: number) {
    if (this.activeNews.length <= 1) {
      return;
    }

    this.activeNews.splice(index, 1);
    this.savedMessage = '';
  }

  moveNewsItem(index: number, direction: -1 | 1) {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= this.activeNews.length) {
      return;
    }

    const [item] = this.activeNews.splice(index, 1);
    this.activeNews.splice(targetIndex, 0, item);
    this.savedMessage = '';
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
      ? `linear-gradient(180deg, rgba(4, 10, 22, 0.12), rgba(4, 10, 22, 0.72)), url("${url}")`
      : '';
  }

  uploadNewsBackground(event: Event, item: CommunityNewsItem) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }

    if (!item.id) {
      this.errorMessage = this.translate.instant('adminContent.feedback.saveBeforeBackgroundUpload');
      input.value = '';
      return;
    }

    this.uploadingBackground[item.id] = true;
    this.errorMessage = '';
    this.savedMessage = '';

    this.homeContent.uploadNewsBackground(item.id, file).subscribe({
      next: updatedItem => {
        item.backgroundUrl = updatedItem.backgroundUrl ?? null;
        item.updated_at = updatedItem.updated_at ?? item.updated_at;
        this.savedMessage = this.translate.instant('adminContent.feedback.backgroundUploadSuccess');
        this.uploadingBackground[item.id!] = false;
        input.value = '';
      },
      error: error => {
        this.errorMessage = error?.error?.error || this.translate.instant('adminContent.feedback.backgroundUploadFailure');
        this.uploadingBackground[item.id!] = false;
        input.value = '';
      }
    });
  }

  removeNewsBackground(item: CommunityNewsItem) {
    item.backgroundUrl = null;
    this.savedMessage = '';
    this.errorMessage = '';
  }

  syncMemberScroll(source: HTMLElement, target: HTMLElement) {
    if (this.syncingMemberScroll) {
      return;
    }

    if (this.memberScrollFrame !== null) {
      return;
    }

    this.memberScrollFrame = requestAnimationFrame(() => {
      this.memberScrollFrame = null;

      const sourceScrollableHeight = source.scrollHeight - source.clientHeight;
      const targetScrollableHeight = target.scrollHeight - target.clientHeight;
      if (sourceScrollableHeight <= 0 || targetScrollableHeight <= 0) {
        return;
      }

      this.syncingMemberScroll = true;
      const scrollRatio = source.scrollTop / sourceScrollableHeight;
      target.scrollTop = scrollRatio * targetScrollableHeight;
      this.syncingMemberScroll = false;
    });
  }

  save() {
    this.saving = true;
    this.savedMessage = '';
    this.errorMessage = '';

    this.homeContent.saveAdminContent(this.content).subscribe({
      next: content => {
        this.content = content;
        this.savedMessage = this.translate.instant('adminContent.feedback.saveSuccess');
        this.saving = false;
      },
      error: error => {
        this.errorMessage = error?.error?.error || this.translate.instant('adminContent.feedback.saveFailure');
        this.saving = false;
      }
    });
  }

  reset() {
    this.content = this.homeContent.getDefaultContent();
    this.savedMessage = this.translate.instant('adminContent.feedback.defaultsLoaded');
    this.errorMessage = '';
  }
}
