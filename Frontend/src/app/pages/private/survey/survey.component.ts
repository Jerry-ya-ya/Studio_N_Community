import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy, OnInit } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';

import { FormQuestion } from '../../../core/services/form-builder.service';
import {
  SurveyAnswer,
  SurveyForm,
  SurveyService
} from '../../../core/services/survey.service';

interface SurveyDraft {
  formId: number;
  formVersion: number;
  answers: Record<string, SurveyAnswer>;
  savedAt: string;
}

@Component({
  selector: 'app-survey',
  standalone: false,
  templateUrl: './survey.component.html',
  styleUrl: './survey.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SurveyComponent implements OnInit, OnDestroy {
  private static readonly draftStoragePrefix = 'private.survey.draft.v1';
  private static readonly autosaveDelayMs = 800;

  forms: SurveyForm[] = [];
  selectedForm: SurveyForm | null = null;
  answers: Record<string, SurveyAnswer> = {};
  loading = false;
  submitting = false;
  errorKey = '';
  errorText = '';
  successKey = '';
  invalidQuestionIds = new Set<string>();
  private readonly draftOwner = this.getCurrentDraftOwner();
  private autosaveTimer: ReturnType<typeof setTimeout> | null = null;
  private hasDraftChanges = false;

  constructor(
    private surveyService: SurveyService,
    private cdr: ChangeDetectorRef,
    private snackBar: MatSnackBar,
    private translate: TranslateService
  ) {}

  ngOnInit(): void {
    this.loadForms();
  }

  ngOnDestroy(): void {
    this.flushDraft();
  }

  loadForms(preferredId?: number): void {
    this.flushDraft();
    this.loading = true;
    this.clearFeedback();
    this.surveyService.listForms().subscribe({
      next: forms => {
        this.forms = forms;
        this.loading = false;
        const selectedId = preferredId ?? this.selectedForm?.id;
        this.selectedForm = forms.find(form => form.id === selectedId) ?? null;
        this.initializeAnswers(this.selectedForm);
        this.cdr.markForCheck();
      },
      error: error => {
        this.loading = false;
        this.setRequestError(error, 'survey.feedback.loadFailure');
      }
    });
  }

  selectForm(form: SurveyForm): void {
    if (this.submitting) {
      return;
    }
    if (this.selectedForm?.id === form.id && this.selectedForm.version === form.version) {
      return;
    }
    this.flushDraft();
    this.selectedForm = form;
    this.initializeAnswers(form);
    this.invalidQuestionIds.clear();
    this.clearFeedback();
    this.cdr.markForCheck();
  }

  isChecked(questionId: string, optionId: string): boolean {
    const value = this.answers[questionId];
    return Array.isArray(value) && value.includes(optionId);
  }

  toggleOption(questionId: string, optionId: string, checked: boolean): void {
    const current = this.answers[questionId];
    const values = Array.isArray(current) ? [...current] : [];
    this.answers[questionId] = checked
      ? Array.from(new Set([...values, optionId]))
      : values.filter(value => value !== optionId);
    this.answerChanged(questionId);
  }

  answerChanged(questionId: string): void {
    this.invalidQuestionIds.delete(questionId);
    this.errorKey = '';
    this.errorText = '';
    this.hasDraftChanges = true;
    this.scheduleAutosave();
  }

  submit(): void {
    const form = this.selectedForm;
    if (!form || form.submitted || this.submitting || !this.validateAnswers(form)) {
      return;
    }
    this.submitting = true;
    this.clearFeedback();
    this.surveyService.submit(form.id, form.version, this.answers).subscribe({
      next: submission => {
        this.submitting = false;
        this.cancelAutosave();
        this.removeDraft(form);
        this.hasDraftChanges = false;
        this.successKey = 'survey.feedback.submitSuccess';
        this.forms = this.forms.map(item => item.id === form.id
          ? { ...item, submitted: true, submittedAt: submission.submittedAt }
          : item
        );
        this.selectedForm = this.forms.find(item => item.id === form.id) ?? null;
        this.cdr.markForCheck();
      },
      error: error => {
        this.submitting = false;
        const fallback = error?.error?.code === 'version_conflict'
          ? 'survey.feedback.versionConflict'
          : error?.error?.code === 'already_submitted'
            ? 'survey.feedback.alreadySubmitted'
            : 'survey.feedback.submitFailure';
        this.setRequestError(error, fallback);
      }
    });
  }

  trackQuestion(_index: number, question: FormQuestion): string {
    return question.id;
  }

  private validateAnswers(form: SurveyForm): boolean {
    this.invalidQuestionIds.clear();
    for (const question of form.schema.questions) {
      const value = this.answers[question.id];
      if (question.required && this.isEmpty(value)) {
        this.invalidQuestionIds.add(question.id);
      }
    }
    if (this.invalidQuestionIds.size) {
      this.errorKey = 'survey.feedback.required';
      this.cdr.markForCheck();
      return false;
    }
    return true;
  }

  private isEmpty(value: SurveyAnswer | undefined): boolean {
    return value === null || value === undefined ||
      (typeof value === 'string' && !value.trim()) ||
      (Array.isArray(value) && value.length === 0);
  }

  private initializeAnswers(form: SurveyForm | null): void {
    this.cancelAutosave();
    this.hasDraftChanges = false;
    this.answers = {};
    if (!form || form.submitted) {
      return;
    }
    for (const question of form.schema.questions) {
      this.answers[question.id] = question.type === 'multiple_choice' ? [] : null;
    }
    const draft = this.readDraft(form);
    if (draft) {
      this.answers = { ...this.answers, ...draft.answers };
      this.openDraftSnack('survey.feedback.draftRestored', draft.savedAt);
    }
    this.invalidQuestionIds.clear();
  }

  private scheduleAutosave(): void {
    this.cancelAutosave();
    this.autosaveTimer = setTimeout(() => {
      this.autosaveTimer = null;
      this.persistDraft(true);
    }, SurveyComponent.autosaveDelayMs);
  }

  private flushDraft(): void {
    this.cancelAutosave();
    this.persistDraft(false);
  }

  private persistDraft(showConfirmation: boolean): void {
    const form = this.selectedForm;
    if (!form || form.submitted || !this.hasDraftChanges) {
      return;
    }

    const savedAt = new Date().toISOString();
    const draft: SurveyDraft = {
      formId: form.id,
      formVersion: form.version,
      answers: this.answers,
      savedAt
    };

    try {
      localStorage.setItem(this.getDraftStorageKey(form), JSON.stringify(draft));
      this.hasDraftChanges = false;
      if (showConfirmation) {
        this.openDraftSnack('survey.feedback.draftSaved', savedAt);
      }
    } catch {
      if (showConfirmation) {
        this.snackBar.open(
          this.translate.instant('survey.feedback.draftSaveFailure'),
          this.translate.instant('survey.actions.dismiss'),
          this.snackBarOptions('studio-snackbar-error')
        );
      }
    }
  }

  private readDraft(form: SurveyForm): SurveyDraft | null {
    try {
      const rawDraft = localStorage.getItem(this.getDraftStorageKey(form));
      if (!rawDraft) {
        return null;
      }
      const parsed = JSON.parse(rawDraft) as Partial<SurveyDraft>;
      if (
        parsed.formId !== form.id ||
        parsed.formVersion !== form.version ||
        typeof parsed.savedAt !== 'string' ||
        Number.isNaN(Date.parse(parsed.savedAt)) ||
        !parsed.answers ||
        typeof parsed.answers !== 'object' ||
        Array.isArray(parsed.answers)
      ) {
        this.removeDraft(form);
        return null;
      }

      const answers: Record<string, SurveyAnswer> = {};
      for (const question of form.schema.questions) {
        const value = parsed.answers[question.id];
        if (this.isValidDraftAnswer(question, value)) {
          answers[question.id] = value;
        }
      }
      return { formId: form.id, formVersion: form.version, answers, savedAt: parsed.savedAt };
    } catch {
      this.removeDraft(form);
      return null;
    }
  }

  private isValidDraftAnswer(question: FormQuestion, value: unknown): value is SurveyAnswer {
    if (value === null) {
      return true;
    }
    const optionIds = new Set((question.options ?? []).map(option => option.id));
    switch (question.type) {
      case 'multiple_choice':
        return Array.isArray(value) && value.every(item => typeof item === 'string' && optionIds.has(item));
      case 'single_choice':
      case 'dropdown':
        return typeof value === 'string' && optionIds.has(value);
      case 'number':
        return typeof value === 'number' && Number.isFinite(value);
      case 'boolean':
        return typeof value === 'boolean';
      default:
        return typeof value === 'string';
    }
  }

  private removeDraft(form: SurveyForm): void {
    try {
      localStorage.removeItem(this.getDraftStorageKey(form));
    } catch {
      // Storage can be unavailable in privacy-restricted browser contexts.
    }
  }

  private getDraftStorageKey(form: SurveyForm): string {
    return `${SurveyComponent.draftStoragePrefix}.${encodeURIComponent(this.draftOwner)}.${form.id}.${form.version}`;
  }

  private getCurrentDraftOwner(): string {
    try {
      return localStorage.getItem('username')?.trim() || 'current-user';
    } catch {
      return 'current-user';
    }
  }

  private openDraftSnack(messageKey: string, savedAt: string): void {
    this.snackBar.open(
      this.translate.instant(messageKey, { time: new Date(savedAt).toLocaleString() }),
      this.translate.instant('survey.actions.dismiss'),
      this.snackBarOptions('studio-snackbar-success')
    );
  }

  private snackBarOptions(panelClass: string) {
    return {
      duration: 3500,
      horizontalPosition: 'right' as const,
      verticalPosition: 'top' as const,
      panelClass: ['studio-snackbar', panelClass]
    };
  }

  private cancelAutosave(): void {
    if (this.autosaveTimer !== null) {
      clearTimeout(this.autosaveTimer);
      this.autosaveTimer = null;
    }
  }

  private clearFeedback(): void {
    this.errorKey = '';
    this.errorText = '';
    this.successKey = '';
  }

  private setRequestError(error: any, fallbackKey: string): void {
    const serverError = error?.error?.error;
    this.errorText = typeof serverError === 'string' ? serverError : '';
    this.errorKey = this.errorText ? '' : fallbackKey;
    this.cdr.markForCheck();
  }
}
