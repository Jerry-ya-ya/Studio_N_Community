import { ChangeDetectorRef } from '@angular/core';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '../../../core/services/api.service';
import { AchievementComponent } from './achievement.component';

describe('AchievementComponent', () => {
  let api: Pick<ApiService, 'get' | 'createAuthHeaders'>;
  let changeDetector: Pick<ChangeDetectorRef, 'markForCheck'>;

  beforeEach(() => {
    api = { get: vi.fn(), createAuthHeaders: vi.fn() };
    changeDetector = { markForCheck: vi.fn() };
  });

  it('defines 15 achievements across check-ins, projects, tokens, tasks, posts and friends', () => {
    const component = new AchievementComponent(api as ApiService, changeDetector as ChangeDetectorRef);

    expect(component.achievements).toHaveLength(15);
    expect(new Set(component.achievements.map(achievement => achievement.key)).size).toBe(15);
    expect(component.achievements.map(achievement => achievement.stat)).toEqual(expect.arrayContaining([
      'totalCheckIns',
      'longestCheckInStreak',
      'createdProjects',
      'projectTokensUsed',
      'completedTodos',
      'createdPosts',
      'friends',
      'coins'
    ]));
  });

  it('maps profile statistics to each achievement and unlocks reached targets', () => {
    vi.mocked(api.get).mockReturnValue(of({
      coins: 100,
      achievementStats: {
        totalCheckIns: 7,
        longestCheckInStreak: 3,
        createdProjects: 1,
        projectTokensUsed: 100,
        completedTodos: 1,
        createdPosts: 1,
        friends: 5
      }
    }));
    const component = new AchievementComponent(api as ApiService, changeDetector as ChangeDetectorRef);

    component.ngOnInit();

    expect(component.achievements.find(achievement => achievement.key === 'firstPotOfGold')).toEqual(expect.objectContaining({
      progress: 100,
      target: 100,
      unlocked: true
    }));
    expect(component.achievements.find(achievement => achievement.key === 'checkInWeek')?.unlocked).toBe(true);
    expect(component.achievements.find(achievement => achievement.key === 'streakWeek')?.unlocked).toBe(false);
    expect(component.achievements.find(achievement => achievement.key === 'tokenSpender')?.unlocked).toBe(true);
    expect(component.unlockedCount).toBe(9);
    expect(component.loading).toBe(false);
  });

  it('keeps 第一桶金 in progress before the user reaches 100 coins and defaults missing stats to zero', () => {
    vi.mocked(api.get).mockReturnValue(of({ total_coins: 99 }));
    const component = new AchievementComponent(api as ApiService, changeDetector as ChangeDetectorRef);

    component.ngOnInit();

    const coinAchievement = component.achievements.find(achievement => achievement.key === 'firstPotOfGold')!;
    expect(coinAchievement.progress).toBe(99);
    expect(coinAchievement.unlocked).toBe(false);
    expect(component.progressPercent(coinAchievement)).toBe(99);
    expect(component.achievements.find(achievement => achievement.key === 'firstProject')?.progress).toBe(0);
  });

  it('caps visual progress at 100 percent when the balance exceeds the target', () => {
    vi.mocked(api.get).mockReturnValue(of({ totalCoins: 250 }));
    const component = new AchievementComponent(api as ApiService, changeDetector as ChangeDetectorRef);

    component.ngOnInit();

    const coinAchievement = component.achievements.find(achievement => achievement.key === 'firstPotOfGold')!;
    expect(component.progressPercent(coinAchievement)).toBe(100);
  });

  it('shows the load failure state when the profile request fails', () => {
    vi.mocked(api.get).mockReturnValue(throwError(() => new Error('network error')));
    const component = new AchievementComponent(api as ApiService, changeDetector as ChangeDetectorRef);

    component.ngOnInit();

    expect(component.loading).toBe(false);
    expect(component.loadFailed).toBe(true);
    expect(changeDetector.markForCheck).toHaveBeenCalled();
  });
});
