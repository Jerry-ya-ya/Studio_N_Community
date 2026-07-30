import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CheckInService, CheckInStatus } from '../../../core/services/check-in.service';
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

  constructor(
    private checkInService: CheckInService,
    private changeDetectorRef: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.loadStatus();
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
