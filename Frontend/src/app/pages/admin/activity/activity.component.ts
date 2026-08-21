import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ActivityPayload, ActivityPromotion, ActivityService, ActivityVisibility } from '../../../core/services/activity.service';

interface ActivityDraft {
  localId: number;
  id: number | null;
  title: string;
  description: string;
  visibility: ActivityVisibility;
  targetFilter: string;
  activityDate: string;
  activityDateValue: Date | null;
  startTime: string;
  endTime: string;
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
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class ActivityComponent implements OnInit {
  readonly visibilityOptions: ActivityVisibility[] = ['public', 'private'];
  readonly targetOptions = ['all', 'role:user', 'role:member', 'role:admin', 'role:superadmin'];

  activities: ActivityDraft[] = [];
  activeVisibility: ActivityVisibility = 'public';
  loading = false;
  savedMessage = '';
  errorMessage = '';

  constructor(
    private activityService: ActivityService,
    private cdr: ChangeDetectorRef
  ) {}

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
        this.cdr.markForCheck();
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'adminActivity.feedback.loadFailure';
        this.loading = false;
        this.cdr.markForCheck();
      }
    });
  }

  addActivity() {
    this.activities = [
      this.createDraft({
        title: '',
        description: '',
        visibility: this.activeVisibility,
        targetFilter: 'all',
        activityDate: this.todayInputValue(),
        activityDateValue: new Date(),
        startTime: '09:00',
        endTime: '18:00',
        sort_order: this.filteredActivities.length
      }),
      ...this.activities
    ];
  }

  get filteredActivities() {
    return this.activities.filter(activity => activity.visibility === this.activeVisibility);
  }

  countByVisibility(visibility: ActivityVisibility) {
    return this.activities.filter(activity => activity.visibility === visibility).length;
  }

  setVisibilityFilter(visibility: ActivityVisibility) {
    this.activeVisibility = visibility;
  }

  isKnownTargetOption(targetFilter: string) {
    return this.targetOptions.includes(targetFilter);
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
        this.refreshActivity(activity);

        if (activity.pendingImageFile && activity.id) {
          this.uploadPendingImage(activity);
        }
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'adminActivity.feedback.saveFailure';
        activity.saving = false;
        this.refreshActivity(activity);
      }
    });
  }

  removeActivity(activity: ActivityDraft) {
    if (!activity.id) {
      this.activities = this.activities.filter(item => item.localId !== activity.localId);
      this.cdr.markForCheck();
      return;
    }

    activity.saving = true;
    this.errorMessage = '';
    this.savedMessage = '';

    this.activityService.deleteActivity(activity.id).subscribe({
      next: () => {
        this.activities = this.activities.filter(item => item.localId !== activity.localId);
        this.savedMessage = 'adminActivity.feedback.deleteSuccess';
        this.cdr.markForCheck();
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'adminActivity.feedback.deleteFailure';
        activity.saving = false;
        this.refreshActivity(activity);
      }
    });
  }

  clearImage(activity: ActivityDraft) {
    if (!activity.id) {
      activity.imageName = '';
      activity.imagePreview = '';
      activity.imageUrl = null;
      activity.pendingImageFile = null;
      this.refreshActivity(activity);
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
        this.refreshActivity(activity);
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'adminActivity.feedback.imageRemoveFailure';
        activity.uploading = false;
        this.refreshActivity(activity);
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
    reader.onload = () => {
      activity.imagePreview = String(reader.result || '');
      this.refreshActivity(activity);
    };
    reader.readAsDataURL(file);
    input.value = '';
  }

  previewImage(activity: ActivityDraft): string {
    return activity.imagePreview || this.activityService.resolveImageUrl(activity.imageUrl);
  }

  getTargetPreviewLabel(activity: ActivityDraft) {
    return activity.targetFilter && this.isKnownTargetOption(activity.targetFilter)
      ? `adminActivity.targetOptions.${activity.targetFilter}`
      : activity.targetFilter || 'all';
  }

  getPreviewActivityTime(activity: ActivityDraft) {
    const dateValue = this.getDateFromPicker(activity);
    const startAt = this.combineDateTime(dateValue, activity.startTime);
    const endAt = this.combineDateTime(dateValue, activity.endTime);

    if (!startAt && !endAt) {
      return 'Time pending';
    }

    const startText = startAt ? this.formatActivityDateTime(startAt) : 'Open start';
    const endText = endAt ? this.formatActivityDateTime(endAt) : 'Open end';
    return `${startText} - ${endText}`;
  }

  isPreviewEnded(activity: ActivityDraft) {
    const endAt = this.combineDateTime(this.getDateFromPicker(activity), activity.endTime);
    return endAt ? new Date(endAt).getTime() <= Date.now() : false;
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
        this.refreshActivity(activity);
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'adminActivity.feedback.imageUploadFailure';
        activity.uploading = false;
        this.refreshActivity(activity);
      }
    });
  }

  private refreshActivity(activity: ActivityDraft) {
    this.activities = this.activities.map(item => item.localId === activity.localId ? { ...activity } : item);
    this.cdr.markForCheck();
  }

  private toPayload(activity: ActivityDraft): ActivityPayload {
    return {
      title: activity.title.trim(),
      description: activity.description.trim(),
      visibility: activity.visibility,
      targetFilter: activity.targetFilter.trim() || 'all',
      startAt: this.combineDateTime(this.getDateFromPicker(activity), activity.startTime),
      endAt: this.combineDateTime(this.getDateFromPicker(activity), activity.endTime),
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
      activityDate: this.getDateInputValue(activity.startAt || activity.start_at || activity.endAt || activity.end_at),
      activityDateValue: this.getDatePickerValue(activity.startAt || activity.start_at || activity.endAt || activity.end_at),
      startTime: this.getTimeInputValue(activity.startAt || activity.start_at),
      endTime: this.getTimeInputValue(activity.endAt || activity.end_at),
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
    activity.activityDate = this.getDateInputValue(saved.startAt || saved.start_at || saved.endAt || saved.end_at);
    activity.activityDateValue = this.getDatePickerValue(saved.startAt || saved.start_at || saved.endAt || saved.end_at);
    activity.startTime = this.getTimeInputValue(saved.startAt || saved.start_at);
    activity.endTime = this.getTimeInputValue(saved.endAt || saved.end_at);
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
      activityDate: '',
      activityDateValue: null,
      startTime: '',
      endTime: '',
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

  private combineDateTime(dateValue: string, timeValue: string) {
    if (!dateValue || !timeValue) {
      return null;
    }

    return `${dateValue}T${timeValue}:00`;
  }

  private getDateFromPicker(activity: ActivityDraft) {
    if (activity.activityDateValue) {
      return this.formatDateForInput(activity.activityDateValue);
    }

    return activity.activityDate;
  }

  private getDateInputValue(value?: string | null) {
    return value ? value.slice(0, 10) : '';
  }

  private getDatePickerValue(value?: string | null) {
    const dateValue = this.getDateInputValue(value);
    return dateValue ? new Date(`${dateValue}T00:00:00`) : null;
  }

  private getTimeInputValue(value?: string | null) {
    return value ? value.slice(11, 16) : '';
  }

  private todayInputValue() {
    return this.formatDateForInput(new Date());
  }

  private formatDateForInput(date: Date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
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
