import { ChangeDetectorRef } from '@angular/core';
import { of } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiService } from '../../../core/services/api.service';
import { SpecialAbilitiesComponent } from './special-abilities.component';


describe('SpecialAbilitiesComponent', () => {
  let api: ApiService;
  let getMock: ReturnType<typeof vi.fn>;
  let postMock: ReturnType<typeof vi.fn>;
  let component: SpecialAbilitiesComponent;
  const status = {
    active: true,
    activatedAt: '2026-09-16T12:00:00+08:00',
    expiresAt: '2026-09-16T12:10:00+08:00',
    remainingSeconds: 600,
    minimumMinutes: 10,
    maximumMinutes: 30
  };

  beforeEach(() => {
    getMock = vi.fn();
    postMock = vi.fn();
    api = { get: getMock, post: postMock } as unknown as ApiService;
    const cdr = {
      markForCheck: vi.fn()
    } as unknown as ChangeDetectorRef;
    component = new SpecialAbilitiesComponent(api, cdr);
  });

  afterEach(() => component.ngOnDestroy());

  it('loads the current override state', () => {
    getMock.mockReturnValue(of(status));

    component.ngOnInit();

    expect(getMock).toHaveBeenCalledWith(
      '/superadmin/special-abilities/api-rate-limit'
    );
    expect(component.status).toEqual(status);
    expect(component.remainingTime).toBe('10:00');
    expect(component.loading).toBe(false);
  });

  it('activates only the selected duration', () => {
    component.durationMinutes = 25;
    postMock.mockReturnValue(of(status));

    component.activate();

    expect(postMock).toHaveBeenCalledWith(
      '/superadmin/special-abilities/api-rate-limit',
      { durationMinutes: 25 }
    );
    expect(component.feedbackKey).toBe('specialAbilities.feedback.activated');
    expect(component.feedbackError).toBe(false);
  });
});
