import { ChangeDetectorRef, Component, NgZone, OnInit } from '@angular/core';
import { timeout } from 'rxjs/operators';
import { TranslateService } from '@ngx-translate/core';
import { ActivityPromotion, ActivityService } from '../../../core/services/activity.service';

@Component({
  selector: 'app-activities',
  standalone: false,
  templateUrl: './activities.component.html',
  styleUrl: './activities.component.css',
})
export class ActivitiesComponent implements OnInit {
  activities: ActivityPromotion[] = [];
  loading = false;
  errorMessage = '';

  constructor(
    private activityService: ActivityService,
    private translate: TranslateService,
    private zone: NgZone,
    private changeDetector: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadActivities();
  }

  loadActivities() {
    this.zone.run(() => {
      this.loading = true;
      this.errorMessage = '';
      this.changeDetector.detectChanges();
    });

    this.activityService.getPublicActivities().pipe(timeout(10000)).subscribe({
      next: activities => {
        this.zone.run(() => {
          this.activities = Array.isArray(activities)
            ? activities.filter(activity => activity.visibility === 'public')
            : [];
          this.loading = false;
          this.changeDetector.detectChanges();
        });
      },
      error: error => {
        this.zone.run(() => {
          this.activities = [];
          this.errorMessage = error?.error?.error || 'activity.state.error';
          this.loading = false;
          this.changeDetector.detectChanges();
        });
      }
    });
  }

  resolveImageUrl(activity: ActivityPromotion) {
    return this.activityService.resolveImageUrl(activity.imageUrl || activity.image_url);
  }

  isEnded(activity: ActivityPromotion) {
    return activity.isEnded || activity.is_ended || activity.status === 'ended';
  }
  getTargetFilterLabel(activity: ActivityPromotion) {
    const target = String(activity.targetFilter || activity.target_filter || 'all').toLowerCase();
    const knownTargets = ['all', 'admin', 'member', 'user', 'superadmin'];
    return knownTargets.includes(target) ? `activity.target.${target}` : target;
  }
  formatCreatedAt(activity: ActivityPromotion) {
    return this.formatActivityDateTime(activity.created_at || '');
  }

  getActivityTime(activity: ActivityPromotion) {
    const startAt = activity.startAt || activity.start_at;
    const endAt = activity.endAt || activity.end_at;

    if (!startAt && !endAt) {
      return this.translate.instant('activity.time.pending');
    }

    const startText = startAt ? this.formatActivityDateTime(startAt) : this.translate.instant('activity.time.openStart');
    const endText = endAt ? this.formatActivityDateTime(endAt) : this.translate.instant('activity.time.openEnd');
    return `${startText} - ${endText}`;
  }

  private formatActivityDateTime(value: string) {
    const date = new Date(value);
    if (!Number.isNaN(date.getTime())) {
      return this.formatDateParts(
        date.getFullYear(),
        date.getMonth() + 1,
        date.getDate(),
        date.getHours(),
        date.getMinutes()
      );
    }

    const normalized = value.trim().replace('T', ' ');
    const match = normalized.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s+(\d{1,2}):(\d{2})/);
    if (!match) {
      return value.replace(/:\d{2}(\.\d+)?([+-]\d{2}:?\d{2}|Z)?$/, '').trim();
    }

    return this.formatDateParts(
      Number(match[1]),
      Number(match[2]),
      Number(match[3]),
      Number(match[4]),
      Number(match[5])
    );
  }

  private formatDateParts(year: number, month: number, day: number, hour: number, minute: number) {
    return `${year}/${this.padDatePart(month)}/${this.padDatePart(day)} ${this.padDatePart(hour)}:${this.padDatePart(minute)}`;
  }

  private padDatePart(value: number) {
    return String(value).padStart(2, '0');
  }
}
