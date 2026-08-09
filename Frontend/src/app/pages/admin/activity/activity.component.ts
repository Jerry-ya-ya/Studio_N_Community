import { Component } from '@angular/core';

type ActivityVisibility = 'public' | 'private';

interface ActivityDraft {
  id: number;
  title: string;
  description: string;
  visibility: ActivityVisibility;
  targetFilter: string;
  imageName: string;
  imagePreview: string;
}

@Component({
  selector: 'app-activity',
  standalone: false,
  templateUrl: './activity.component.html',
  styleUrl: './activity.component.css',
})
export class ActivityComponent {
  readonly visibilityOptions: ActivityVisibility[] = ['public', 'private'];

  activities: ActivityDraft[] = [
    this.createDraft({
      title: 'Season Launch Signal',
      description: 'A featured activity banner ready for the next community update.',
      visibility: 'public',
      targetFilter: 'all'
    })
  ];

  addActivity() {
    this.activities = [
      this.createDraft({
        title: '',
        description: '',
        visibility: 'private',
        targetFilter: 'role:member'
      }),
      ...this.activities
    ];
  }

  removeActivity(activityId: number) {
    this.activities = this.activities.filter(activity => activity.id !== activityId);
  }

  clearImage(activity: ActivityDraft) {
    activity.imageName = '';
    activity.imagePreview = '';
  }

  onImageSelected(event: Event, activity: ActivityDraft) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];

    if (!file) {
      return;
    }

    activity.imageName = file.name;

    const reader = new FileReader();
    reader.onload = () => activity.imagePreview = String(reader.result || '');
    reader.readAsDataURL(file);
    input.value = '';
  }

  private createDraft(overrides: Partial<ActivityDraft>): ActivityDraft {
    return {
      id: Date.now() + Math.floor(Math.random() * 1000),
      title: '',
      description: '',
      visibility: 'private',
      targetFilter: '',
      imageName: '',
      imagePreview: '',
      ...overrides
    };
  }
}
