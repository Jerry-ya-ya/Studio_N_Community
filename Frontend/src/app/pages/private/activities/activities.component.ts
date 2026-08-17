import { Component, OnInit } from '@angular/core';
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

  constructor(private activityService: ActivityService) {}

  ngOnInit() {
    this.loadActivities();
  }

  loadActivities() {
    this.loading = true;
    this.errorMessage = '';

    this.activityService.getPrivateActivities().subscribe({
      next: activities => {
        this.activities = activities;
        this.loading = false;
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'Unable to load private activities.';
        this.loading = false;
      }
    });
  }

  resolveImageUrl(activity: ActivityPromotion) {
    return this.activityService.resolveImageUrl(activity.imageUrl || activity.image_url);
  }
}
