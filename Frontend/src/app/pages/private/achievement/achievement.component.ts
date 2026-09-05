import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { ApiService } from '../../../core/services/api.service';

interface Achievement {
  key: string;
  icon: string;
  stat: keyof AchievementStats;
  unit: string;
  progress: number;
  target: number;
  unlocked: boolean;
}

interface AchievementStats {
  coins: number;
  totalCheckIns: number;
  longestCheckInStreak: number;
  createdProjects: number;
  projectTokensUsed: number;
  completedTodos: number;
  createdPosts: number;
  friends: number;
}

interface CurrentUser {
  coins?: number;
  total_coins?: number;
  totalCoins?: number;
  achievementStats?: Partial<Omit<AchievementStats, 'coins'>>;
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
    { key: 'firstCheckIn', icon: '🌱', stat: 'totalCheckIns', unit: 'days', progress: 0, target: 1, unlocked: false },
    { key: 'checkInWeek', icon: '📅', stat: 'totalCheckIns', unit: 'days', progress: 0, target: 7, unlocked: false },
    { key: 'checkInMonth', icon: '🗓️', stat: 'totalCheckIns', unit: 'days', progress: 0, target: 30, unlocked: false },
    { key: 'streakThree', icon: '🔥', stat: 'longestCheckInStreak', unit: 'days', progress: 0, target: 3, unlocked: false },
    { key: 'streakWeek', icon: '⚡', stat: 'longestCheckInStreak', unit: 'days', progress: 0, target: 7, unlocked: false },
    { key: 'streakMonth', icon: '☀️', stat: 'longestCheckInStreak', unit: 'days', progress: 0, target: 30, unlocked: false },
    { key: 'firstProject', icon: '🚀', stat: 'createdProjects', unit: 'projects', progress: 0, target: 1, unlocked: false },
    { key: 'projectBuilder', icon: '🏗️', stat: 'createdProjects', unit: 'projects', progress: 0, target: 5, unlocked: false },
    { key: 'tokenSpender', icon: '🧩', stat: 'projectTokensUsed', unit: 'tokens', progress: 0, target: 100, unlocked: false },
    { key: 'tokenMaster', icon: '💠', stat: 'projectTokensUsed', unit: 'tokens', progress: 0, target: 500, unlocked: false },
    { key: 'firstTask', icon: '✅', stat: 'completedTodos', unit: 'tasks', progress: 0, target: 1, unlocked: false },
    { key: 'taskMaster', icon: '🏆', stat: 'completedTodos', unit: 'tasks', progress: 0, target: 10, unlocked: false },
    { key: 'firstPost', icon: '✍️', stat: 'createdPosts', unit: 'posts', progress: 0, target: 1, unlocked: false },
    { key: 'socialCircle', icon: '🤝', stat: 'friends', unit: 'friends', progress: 0, target: 5, unlocked: false },
    { key: 'firstPotOfGold', icon: '🪙', stat: 'coins', unit: 'coins', progress: 0, target: 100, unlocked: false }
  ];
  loading = true;
  loadFailed = false;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.api.get<CurrentUser>('/me', this.api.createAuthHeaders()).subscribe({
      next: user => {
        const coins = Number(user.coins ?? user.total_coins ?? user.totalCoins ?? 0);
        const rawStats = user.achievementStats ?? {};
        const stats: AchievementStats = {
          coins: this.normalizeProgress(coins),
          totalCheckIns: this.normalizeProgress(rawStats.totalCheckIns),
          longestCheckInStreak: this.normalizeProgress(rawStats.longestCheckInStreak),
          createdProjects: this.normalizeProgress(rawStats.createdProjects),
          projectTokensUsed: this.normalizeProgress(rawStats.projectTokensUsed),
          completedTodos: this.normalizeProgress(rawStats.completedTodos),
          createdPosts: this.normalizeProgress(rawStats.createdPosts),
          friends: this.normalizeProgress(rawStats.friends)
        };
        this.achievements = this.achievements.map(achievement => ({
          ...achievement,
          progress: stats[achievement.stat],
          unlocked: stats[achievement.stat] >= achievement.target
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

  private normalizeProgress(value: unknown): number {
    const progress = Number(value ?? 0);
    return Number.isFinite(progress) ? Math.max(0, progress) : 0;
  }
}
