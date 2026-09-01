import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CheckInHistory, CheckInService, CheckInStatus } from '../../../core/services/check-in.service';
import { finalize } from 'rxjs';

@Component({
  selector: 'app-check-in',
  standalone: false,
  templateUrl: './check-in.component.html',
  styleUrl: './check-in.component.css',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class CheckInComponent implements OnInit {
  status: CheckInStatus | null = null;
  loading = false;
  checkingIn = false;
  errorMessage = '';
  successMessage = '';
  historyLoading = false;
  historyError = '';
  selectedYear = new Date().getFullYear();
  availableYears = [this.selectedYear];
  calendarDays: { date: string; checked: boolean; outsideYear: boolean }[] = [];
  readonly weekdays = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];

  constructor(
    private checkInService: CheckInService,
    private changeDetectorRef: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadStatus();
    this.loadHistory(this.selectedYear);
  }

  loadHistory(year: number) {
    this.selectedYear = Number(year);
    this.historyLoading = true;
    this.historyError = '';
    this.checkInService.getHistory(this.selectedYear).pipe(
      finalize(() => {
        this.historyLoading = false;
        this.changeDetectorRef.detectChanges();
      })
    ).subscribe({
      next: history => this.applyHistory(history),
      error: error => {
        this.historyError = error?.error?.error || 'checkIn.history.loadFailure';
        this.calendarDays = [];
      }
    });
  }

  private applyHistory(history: CheckInHistory) {
    this.availableYears = history.availableYears;
    const checkedDates = new Set(history.checkedDates);
    const firstDay = new Date(history.year, 0, 1);
    const gridStart = new Date(history.year, 0, 1 - firstDay.getDay());
    const lastDay = new Date(history.year, 11, 31);
    const gridEnd = new Date(history.year, 11, 31 + (6 - lastDay.getDay()));
    const days = [];

    for (const cursor = new Date(gridStart); cursor <= gridEnd; cursor.setDate(cursor.getDate() + 1)) {
      const date = this.toLocalDateKey(cursor);
      days.push({ date, checked: checkedDates.has(date), outsideYear: cursor.getFullYear() !== history.year });
    }
    this.calendarDays = days;
  }

  private toLocalDateKey(value: Date) {
    const month = String(value.getMonth() + 1).padStart(2, '0');
    const day = String(value.getDate()).padStart(2, '0');
    return `${value.getFullYear()}-${month}-${day}`;
  }

  loadStatus() {
    this.loading = true;
    this.errorMessage = '';

    this.checkInService.getStatus().pipe(
      finalize(() => {
        this.loading = false;
        this.changeDetectorRef.detectChanges();
      })
    ).subscribe({
      next: status => {
        this.status = { ...status };
        this.loadHistory(this.selectedYear);
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'checkIn.feedback.loadFailure';
      }
    });
  }

  checkIn() {
    if (this.status?.checkedInToday || this.checkingIn) {
      return;
    }

    this.checkingIn = true;
    this.errorMessage = '';
    this.successMessage = '';

    this.checkInService.checkIn().pipe(
      finalize(() => {
        this.checkingIn = false;
        this.changeDetectorRef.detectChanges();
      })
    ).subscribe({
      next: status => {
        this.status = { ...status };
        this.successMessage = status.earnedPoints
          ? 'checkIn.feedback.checkInSuccess'
          : 'checkIn.feedback.alreadyCheckedIn';
      },
      error: error => {
        this.errorMessage = error?.error?.error || 'checkIn.feedback.checkInFailure';
      }
    });
  }
}
