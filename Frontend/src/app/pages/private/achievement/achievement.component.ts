import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';

interface Achievement {
  key: string;
  icon: string;
  progress: number;
  target: number;
  unlocked: boolean;
}

interface CurrentUser {
  coins?: number;
  total_coins?: number;
  totalCoins?: number;
}

@Component({
  selector: 'app-achievement',
  standalone: false,
  templateUrl: './achievement.component.html',
  styleUrl: './achievement.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AchievementComponent implements OnInit {
  achievements: Achievement[] = [
    { key: 'firstPotOfGold', icon: '🪙', progress: 0, target: 100, unlocked: false }
  ];
  loading = true;
  loadFailed = false;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.api.get<CurrentUser>('/me', this.api.createAuthHeaders()).subscribe({
      next: user => {
        const coins = Number(user.coins ?? user.total_coins ?? user.totalCoins ?? 0);
        const progress = Number.isFinite(coins) ? Math.max(0, coins) : 0;
        this.achievements = this.achievements.map(achievement => ({
          ...achievement,
          progress,
          unlocked: progress >= achievement.target
        }));
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.loadFailed = true;
        this.cdr.markForCheck();
      }
    });
  }

  get unlockedCount(): number {
    return this.achievements.filter(achievement => achievement.unlocked).length;
  }

  progressPercent(achievement: Achievement): number {
    return Math.min(100, Math.round((achievement.progress / achievement.target) * 100));
  }
}
