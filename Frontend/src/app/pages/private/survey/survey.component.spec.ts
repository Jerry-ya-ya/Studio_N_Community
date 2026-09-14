import { ChangeDetectorRef } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { SurveyForm, SurveyService } from '../../../core/services/survey.service';
import { SurveyComponent } from './survey.component';

describe('SurveyComponent draft autosave', () => {
  const form: SurveyForm = {
    id: 12,
    title: 'Member survey',
    description: '',
    version: 3,
    submitted: false,
    submittedAt: null,
    schema: {
      schemaVersion: 1,
      questions: [
        { id: 'name', type: 'short_text', title: 'Name', description: '', required: true, options: [] },
        {
          id: 'topics',
          type: 'multiple_choice',
          title: 'Topics',
          description: '',
          required: false,
          options: [{ id: 'games', label: 'Games' }, { id: 'code', label: 'Code' }]
        }
      ]
    }
  };

  let surveyService: { listForms: ReturnType<typeof vi.fn>; submit: ReturnType<typeof vi.fn> };
  let snackBar: { open: ReturnType<typeof vi.fn> };
  let component: SurveyComponent;

  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    localStorage.setItem('username', 'jack');
    surveyService = { listForms: vi.fn(), submit: vi.fn() };
    snackBar = { open: vi.fn() };
    const changeDetector = { markForCheck: vi.fn() };
    const translate = { instant: vi.fn((key: string) => key) };
    component = new SurveyComponent(
      surveyService as unknown as SurveyService,
      changeDetector as unknown as ChangeDetectorRef,
      snackBar as unknown as MatSnackBar,
      translate as unknown as TranslateService
    );
  });

  afterEach(() => {
    component.ngOnDestroy();
    vi.useRealTimers();
  });

  it('auto-saves changed answers after the debounce and shows the save time', () => {
    component.selectForm(form);
    component.answers['name'] = 'Jack';
    component.answerChanged('name');

    vi.advanceTimersByTime(800);

    const draft = JSON.parse(localStorage.getItem('private.survey.draft.v1.jack.12.3')!);
    expect(draft.answers).toEqual({ name: 'Jack', topics: [] });
    expect(Date.parse(draft.savedAt)).not.toBeNaN();
    expect(snackBar.open).toHaveBeenCalledWith(
      'survey.feedback.draftSaved',
      'survey.actions.dismiss',
      expect.objectContaining({ panelClass: ['studio-snackbar', 'studio-snackbar-success'] })
    );
  });

  it('restores only valid answers from the matching form version and reports the last save time', () => {
    localStorage.setItem('private.survey.draft.v1.jack.12.3', JSON.stringify({
      formId: 12,
      formVersion: 3,
      savedAt: '2026-09-14T01:00:00.000Z',
      answers: { name: 'Restored', topics: ['games'], unknown: 'ignored' }
    }));

    component.selectForm(form);

    expect(component.answers).toEqual({ name: 'Restored', topics: ['games'] });
    expect(snackBar.open).toHaveBeenCalledWith(
      'survey.feedback.draftRestored',
      'survey.actions.dismiss',
      expect.any(Object)
    );
  });

  it('flushes a pending change when the component is destroyed', () => {
    component.selectForm(form);
    component.answers['name'] = 'Lifecycle save';
    component.answerChanged('name');

    component.ngOnDestroy();

    const draft = JSON.parse(localStorage.getItem('private.survey.draft.v1.jack.12.3')!);
    expect(draft.answers['name']).toBe('Lifecycle save');
    expect(snackBar.open).not.toHaveBeenCalled();
  });

  it('removes the draft after a successful submission', () => {
    surveyService.submit.mockReturnValue(of({
      id: 1,
      formId: 12,
      formVersion: 3,
      submittedAt: '2026-09-14T02:00:00.000Z'
    }));
    component.forms = [form];
    component.selectForm(form);
    component.answers['name'] = 'Ready';
    component.answerChanged('name');
    vi.advanceTimersByTime(800);

    component.submit();

    expect(localStorage.getItem('private.survey.draft.v1.jack.12.3')).toBeNull();
    expect(component.selectedForm?.submitted).toBe(true);
  });
});
