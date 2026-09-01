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

  it('unlocks 第一桶金 after earning 100 coins', () => {
    vi.mocked(api.get).mockReturnValue(of({ coins: 100 }));
    const component = new AchievementComponent(api as ApiService, changeDetector as ChangeDetectorRef);

    component.ngOnInit();

    expect(component.achievements[0]).toEqual(expect.objectContaining({
      key: 'firstPotOfGold',
      progress: 100,
      target: 100,
      unlocked: true
    }));
    expect(component.unlockedCount).toBe(1);
    expect(component.loading).toBe(false);
  });

  it('keeps 第一桶金 in progress before the user reaches 100 coins', () => {
    vi.mocked(api.get).mockReturnValue(of({ total_coins: 99 }));
    const component = new AchievementComponent(api as ApiService, changeDetector as ChangeDetectorRef);

    component.ngOnInit();

    expect(component.achievements[0].progress).toBe(99);
    expect(component.achievements[0].unlocked).toBe(false);
    expect(component.progressPercent(component.achievements[0])).toBe(99);
  });

  it('caps visual progress at 100 percent when the balance exceeds the target', () => {
    vi.mocked(api.get).mockReturnValue(of({ totalCoins: 250 }));
    const component = new AchievementComponent(api as ApiService, changeDetector as ChangeDetectorRef);

    component.ngOnInit();

    expect(component.progressPercent(component.achievements[0])).toBe(100);
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
