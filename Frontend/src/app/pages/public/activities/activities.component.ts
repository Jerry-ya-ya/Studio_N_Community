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

  get rawActivitiesJson() {
    return JSON.stringify(this.rawActivities, null, 2);
  }
}
