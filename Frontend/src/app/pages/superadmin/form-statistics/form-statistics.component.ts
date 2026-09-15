import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnDestroy,
  OnInit
} from '@angular/core';

import {
  FormStatistic,
  FormStatisticQuestion,
  FormStatisticsResponse,
  FormStatisticsService
} from '../../../core/services/form-statistics.service';

const REFRESH_INTERVAL_KEY = 'formStatisticsRefreshMinutes';

@Component({
  selector: 'app-form-statistics',
  standalone: false,
  templateUrl: './form-statistics.component.html',
  styleUrl: './form-statistics.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FormStatisticsComponent implements OnInit, OnDestroy {
  readonly intervalOptions = [1, 2, 5, 10];
  data: FormStatisticsResponse | null = null;
  selectedFormId: number | null = null;
  refreshMinutes = this.readRefreshMinutes();
  loading = false;
  refreshing = false;
  error = false;
  nextRefreshAt: Date | null = null;

  private intervalId: ReturnType<typeof setInterval> | null = null;
  private settlementTimerIds: ReturnType<typeof setTimeout>[] = [];
  private destroyed = false;

  constructor(
    private statisticsService: FormStatisticsService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadStatistics(true);
    this.restartInterval();
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    this.clearTimers();
  }

  get selectedForm(): FormStatistic | null {
    return this.data?.forms.find(form => form.id === this.selectedFormId) || null;
  }

  loadStatistics(initial = false): void {
    if (this.refreshing) {
      return;
    }
    this.refreshing = true;
    this.loading = initial && !this.data;
    this.error = false;
    this.cdr.markForCheck();

    this.statisticsService.getStatistics().subscribe({
      next: data => {
        if (this.destroyed) {
          return;
        }
        this.data = data;
        if (!data.forms.some(form => form.id === this.selectedFormId)) {
          this.selectedFormId = data.forms[0]?.id ?? null;
        }
        this.loading = false;
        this.refreshing = false;
        this.nextRefreshAt = new Date(Date.now() + this.refreshMinutes * 60_000);
        this.scheduleSettlementRefreshes(data.forms);
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.refreshing = false;
        this.error = true;
        this.cdr.markForCheck();
      }
    });
  }

  selectForm(formId: number): void {
    this.selectedFormId = formId;
    this.cdr.markForCheck();
  }

  onRefreshIntervalChange(): void {
    localStorage.setItem(REFRESH_INTERVAL_KEY, String(this.refreshMinutes));
    this.restartInterval();
  }

  optionWidth(percentage: number): string {
    return `${Math.max(0, Math.min(100, percentage))}%`;
  }

  questionTypeKey(question: FormStatisticQuestion): string {
    return `formStatistics.types.${question.type}`;
  }

  private restartInterval(): void {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
    }
    this.nextRefreshAt = new Date(Date.now() + this.refreshMinutes * 60_000);
    this.intervalId = setInterval(
      () => this.loadStatistics(),
      this.refreshMinutes * 60_000
    );
    this.cdr.markForCheck();
  }

  private scheduleSettlementRefreshes(forms: FormStatistic[]): void {
    this.settlementTimerIds.forEach(timerId => clearTimeout(timerId));
    this.settlementTimerIds = [];
    const maximumTimeout = 2_147_000_000;
    for (const form of forms) {
      if (form.settled || !form.settlementAt) {
        continue;
      }
      const delay = new Date(form.settlementAt).getTime() - Date.now();
      if (delay > maximumTimeout) {
        continue;
      }
      const timerId = setTimeout(
        () => this.loadStatistics(),
        Math.max(0, delay) + 250
      );
      this.settlementTimerIds.push(timerId);
    }
  }

  private clearTimers(): void {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.settlementTimerIds.forEach(timerId => clearTimeout(timerId));
    this.settlementTimerIds = [];
  }

  private readRefreshMinutes(): number {
    const stored = Number(localStorage.getItem(REFRESH_INTERVAL_KEY));
    return this.intervalOptions.includes(stored) ? stored : 5;
  }
}
