import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnDestroy,
  OnInit
} from '@angular/core';

import { ApiService } from '../../../core/services/api.service';

interface ApiRateLimitOverride {
  active: boolean;
  activatedAt: string | null;
  expiresAt: string | null;
  remainingSeconds: number;
  minimumMinutes: number;
  maximumMinutes: number;
}

const ENDPOINT = '/superadmin/special-abilities/api-rate-limit';

@Component({
  selector: 'app-special-abilities',
  standalone: false,
  templateUrl: './special-abilities.component.html',
  styleUrl: './special-abilities.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SpecialAbilitiesComponent implements OnInit, OnDestroy {
  readonly durationOptions = [10, 15, 20, 25, 30];
  durationMinutes = 10;
  status: ApiRateLimitOverride | null = null;
  loading = true;
  activating = false;
  feedbackKey = '';
  feedbackError = false;

  private countdownId: ReturnType<typeof setInterval> | null = null;

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadStatus();
    this.countdownId = setInterval(() => this.tick(), 1_000);
  }

  ngOnDestroy(): void {
    if (this.countdownId !== null) {
      clearInterval(this.countdownId);
    }
  }

  get remainingTime(): string {
    const seconds = this.status?.remainingSeconds ?? 0;
    const minutes = Math.floor(seconds / 60);
    const remainder = seconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
  }

  loadStatus(): void {
    this.loading = true;
    this.api.get<ApiRateLimitOverride>(ENDPOINT).subscribe({
      next: status => {
        this.status = status;
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.feedbackKey = 'specialAbilities.feedback.loadFailed';
        this.feedbackError = true;
        this.cdr.markForCheck();
      }
    });
  }

  activate(): void {
    if (this.activating || this.durationMinutes < 10 || this.durationMinutes > 30) {
      return;
    }

    this.activating = true;
    this.feedbackKey = '';
    this.api.post<ApiRateLimitOverride>(ENDPOINT, {
      durationMinutes: this.durationMinutes
    }).subscribe({
      next: status => {
        this.status = status;
        this.activating = false;
        this.feedbackKey = 'specialAbilities.feedback.activated';
        this.feedbackError = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.activating = false;
        this.feedbackKey = 'specialAbilities.feedback.activateFailed';
        this.feedbackError = true;
        this.cdr.markForCheck();
      }
    });
  }

  private tick(): void {
    if (!this.status?.active) {
      return;
    }
    this.status = {
      ...this.status,
      remainingSeconds: Math.max(0, this.status.remainingSeconds - 1),
      active: this.status.remainingSeconds > 1
    };
    this.cdr.markForCheck();
  }
}
