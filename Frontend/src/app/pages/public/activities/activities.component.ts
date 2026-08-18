import { ChangeDetectorRef, Component, NgZone, OnInit } from '@angular/core';
import { timeout } from 'rxjs/operators';
import { ActivityPromotion, ActivityService } from '../../../core/services/activity.service';

@Component({
  selector: 'app-activities',
  standalone: false,
  templateUrl: './activities.component.html',
  styleUrl: './activities.component.css',
})
export class ActivitiesComponent implements OnInit {
  activities: ActivityPromotion[] = [];
  rawActivities: ActivityPromotion[] = [];
  loading = false;
  errorMessage = '';

  constructor(
    private activityService: ActivityService,
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
          this.rawActivities = Array.isArray(activities) ? activities : [];
          this.activities = this.rawActivities.filter(activity => activity.visibility === 'public');
          this.loading = false;
          this.changeDetector.detectChanges();
        });
      },
      error: error => {
        this.zone.run(() => {
          this.rawActivities = [];
          this.activities = [];
          this.errorMessage = error?.error?.error || 'Unable to load public activities.';
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

  getActivityTime(activity: ActivityPromotion) {
    const startAt = activity.startAt || activity.start_at;
    const endAt = activity.endAt || activity.end_at;

    if (!startAt && !endAt) {
      return 'Time pending';
    }

    const startText = startAt ? this.formatActivityDateTime(startAt) : 'Open start';
    const endText = endAt ? this.formatActivityDateTime(endAt) : 'Open end';
    return `${startText} - ${endText}`;
  }

  get rawActivitiesJson() {
    return JSON.stringify(this.rawActivities, null, 2);
  }

  private formatActivityDateTime(value: string) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return date.toLocaleString([], {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}
