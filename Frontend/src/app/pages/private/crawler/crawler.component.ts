import { Component, ChangeDetectionStrategy } from '@angular/core';
import { OnDestroy, OnInit } from '@angular/core';

import { HttpClient } from '@angular/common/http';
import { interval, Subscription } from 'rxjs';
import { TranslateService } from '@ngx-translate/core';
import { ApiService } from '../../../core/services/api.service';

@Component({
  selector: 'app-crawler',
  standalone: false,
  templateUrl: './crawler.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './crawler.component.css'
})
export class CrawlerComponent implements OnInit, OnDestroy {
  news: any[] = [];
  scheduleInfo: any = null;
  readonly canTriggerCrawler = ['admin', 'superadmin'].includes(localStorage.getItem('role') || '');
  private updateSubscription: Subscription;
  
  constructor(
    private apiService: ApiService,
    private translate: TranslateService
  ) {
    // 每900秒更新一次時間資訊
    this.updateSubscription = interval(900000).subscribe(() => {
      this.updateScheduleInfo();
    });
  }

  ngOnInit(): void {
    this.loadNews();
    this.updateScheduleInfo();
  }

  ngOnDestroy(): void {
    if (this.updateSubscription) {
      this.updateSubscription.unsubscribe();
    }
  }

  loadNews() {
    this.apiService.get<any>('/crawler/news').subscribe({
      next: (data) => {
        this.news = data;
      },
      error: (error) => {
        console.error('Error loading news:', error);
      }
    });
  }

  updateScheduleInfo() {
    this.apiService.get<any>('/crawler/info').subscribe({
      next: (info) => {
        this.scheduleInfo = info;
      },
      error: (error) => {
        console.error('Error updating schedule info:', error);
      }
    });
  }

  fetchNews() {
    this.apiService.post('/crawler/fetch', {}).subscribe({
      next: () => {
        this.loadNews();
        this.updateScheduleInfo();
      },
      error: (error) => {
        console.error('Error fetching news:', error);
        alert(this.translate.instant('privateCrawler.feedback.fetchFailure'));
      }
    });
  }
}
