import { ChangeDetectionStrategy, Component } from '@angular/core';

interface Achievement {
  key: string;
  icon: string;
  progress: number;
  target: number;
  unlocked: boolean;
}

@Component({
  selector: 'app-achievement',
  standalone: false,
  templateUrl: './achievement.component.html',
  styleUrl: './achievement.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AchievementComponent {
  readonly achievements: Achievement[] = [
    { key: 'firstStep', icon: '🌱', progress: 1, target: 1, unlocked: true },
    { key: 'social', icon: '🤝', progress: 3, target: 5, unlocked: false },
    { key: 'focused', icon: '🎯', progress: 7, target: 10, unlocked: false },
    { key: 'streak', icon: '🔥', progress: 7, target: 7, unlocked: true },
    { key: 'explorer', icon: '🧭', progress: 4, target: 6, unlocked: false },
    { key: 'community', icon: '🌟', progress: 10, target: 10, unlocked: true }
  ];

  get unlockedCount(): number {
    return this.achievements.filter(achievement => achievement.unlocked).length;
  }

  progressPercent(achievement: Achievement): number {
    return Math.min(100, Math.round((achievement.progress / achievement.target) * 100));
  }
}
