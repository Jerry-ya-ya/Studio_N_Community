import { Component, OnInit } from '@angular/core';
import { ActivityPayload, ActivityPromotion, ActivityService, ActivityVisibility } from '../../../core/services/activity.service';

interface ActivityDraft {
  localId: number;
  id: number | null;
  title: string;
  description: string;
  visibility: ActivityVisibility;
  targetFilter: string;
  imageName: string;
  imagePreview: string;
  imageUrl: string | null;
  sort_order: number;
  saving: boolean;
  uploading: boolean;
  pendingImageFile: File | null;
}

@Component({
  selector: 'app-activity',
  standalone: false,
  templateUrl: './activity.component.html',
  styleUrl: './activity.component.css',
})
export class ActivityComponent implements OnInit {
  readonly visibilityOptions: ActivityVisibility[] = ['public', 'private'];

  activities: ActivityDraft[] = [];
  loading = false;
  savedMessage = '';
  errorMessage = '';

  constructor(private activityService: ActivityService) {}

  ngOnInit() {
    this.loadActivities();
  }

  loadActivities() {
    this.loading = true;
    this.errorMessage = '';

    this.activityService.getAdminActivities().subscribe({
      next: activities => {
        this.activities = activities.map((activity, index) => this.fromApi(activity, index));
        this.loading = false;
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'adminActivity.feedback.loadFailure';
        this.loading = false;
      }
    });
  }

  addActivity() {
    this.activities = [
      this.createDraft({
        title: '',
        description: '',
        visibility: 'private',
        targetFilter: 'role:member',
        sort_order: this.activities.length
      }),
      ...this.activities
    ];
  }

  saveActivity(activity: ActivityDraft) {
    const payload = this.toPayload(activity);
    if (!payload.title || !payload.description) {
      this.errorMessage = 'adminActivity.feedback.required';
      return;
    }

    activity.saving = true;
    this.errorMessage = '';
    this.savedMessage = '';

    const request$ = activity.id
      ? this.activityService.updateActivity(activity.id, payload)
      : this.activityService.createActivity(payload);

    request$.subscribe({
      next: saved => {
        this.applySavedActivity(activity, saved);
        this.savedMessage = 'adminActivity.feedback.saveSuccess';
        activity.saving = false;

        if (activity.pendingImageFile && activity.id) {
          this.uploadPendingImage(activity);
        }
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'adminActivity.feedback.saveFailure';
        activity.saving = false;
      }
    });
  }

  removeActivity(activity: ActivityDraft) {
    if (!activity.id) {
      this.activities = this.activities.filter(item => item.localId !== activity.localId);
      return;
    }

    activity.saving = true;
    this.errorMessage = '';
    this.savedMessage = '';

    this.activityService.deleteActivity(activity.id).subscribe({
      next: () => {
        this.activities = this.activities.filter(item => item.localId !== activity.localId);
        this.savedMessage = 'adminActivity.feedback.deleteSuccess';
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'adminActivity.feedback.deleteFailure';
        activity.saving = false;
      }
    });
  }

  clearImage(activity: ActivityDraft) {
    if (!activity.id) {
      activity.imageName = '';
      activity.imagePreview = '';
      activity.imageUrl = null;
      activity.pendingImageFile = null;
      return;
    }

    activity.uploading = true;
    this.activityService.clearActivityImage(activity.id).subscribe({
      next: saved => {
        this.applySavedActivity(activity, saved);
        activity.imageName = '';
        activity.pendingImageFile = null;
        activity.uploading = false;
        this.savedMessage = 'adminActivity.feedback.imageRemoved';
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'adminActivity.feedback.imageRemoveFailure';
        activity.uploading = false;
      }
    });
  }

  onImageSelected(event: Event, activity: ActivityDraft) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file) {
      return;
    }

    activity.imageName = file.name;
    activity.pendingImageFile = file;

    const reader = new FileReader();
    reader.onload = () => activity.imagePreview = String(reader.result || '');
    reader.readAsDataURL(file);
    input.value = '';
  }

  previewImage(activity: ActivityDraft): string {
    return activity.imagePreview || this.activityService.resolveImageUrl(activity.imageUrl);
  }

  private uploadPendingImage(activity: ActivityDraft) {
    if (!activity.id || !activity.pendingImageFile) {
      return;
    }

    activity.uploading = true;
    this.activityService.uploadActivityImage(activity.id, activity.pendingImageFile).subscribe({
      next: saved => {
        this.applySavedActivity(activity, saved);
        activity.pendingImageFile = null;
        activity.uploading = false;
        this.savedMessage = 'adminActivity.feedback.imageUploaded';
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'adminActivity.feedback.imageUploadFailure';
        activity.uploading = false;
      }
    });
  }

  private toPayload(activity: ActivityDraft): ActivityPayload {
    return {
      title: activity.title.trim(),
      description: activity.description.trim(),
      visibility: activity.visibility,
      targetFilter: activity.targetFilter.trim() || 'all',
      sort_order: activity.sort_order,
      imageUrl: activity.imageUrl
    };
  }

  private fromApi(activity: ActivityPromotion, index: number): ActivityDraft {
    return this.createDraft({
      id: activity.id,
      title: activity.title,
      description: activity.description,
      visibility: activity.visibility,
      targetFilter: activity.targetFilter || activity.target_filter || 'all',
      imageUrl: activity.imageUrl || activity.image_url || null,
      sort_order: activity.sort_order ?? index
    });
  }

  private applySavedActivity(activity: ActivityDraft, saved: ActivityPromotion) {
    activity.id = saved.id;
    activity.title = saved.title;
    activity.description = saved.description;
    activity.visibility = saved.visibility;
    activity.targetFilter = saved.targetFilter || saved.target_filter || 'all';
    activity.imageUrl = saved.imageUrl || saved.image_url || null;
    activity.imagePreview = '';
    activity.sort_order = saved.sort_order ?? activity.sort_order;
  }

  private createDraft(overrides: Partial<ActivityDraft>): ActivityDraft {
    return {
      localId: Date.now() + Math.floor(Math.random() * 1000),
      id: null,
      title: '',
      description: '',
      visibility: 'private',
      targetFilter: '',
      imageName: '',
      imagePreview: '',
      imageUrl: null,
      sort_order: 0,
      saving: false,
      uploading: false,
      pendingImageFile: null,
      ...overrides
    };
  }
}
