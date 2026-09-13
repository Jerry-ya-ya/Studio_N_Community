import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';

import { FormQuestion } from '../../../core/services/form-builder.service';
import {
  SurveyAnswer,
  SurveyForm,
  SurveyService
} from '../../../core/services/survey.service';


@Component({
  selector: 'app-survey',
  standalone: false,
  templateUrl: './survey.component.html',
  styleUrl: './survey.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SurveyComponent implements OnInit {
  forms: SurveyForm[] = [];
  selectedForm: SurveyForm | null = null;
  answers: Record<string, SurveyAnswer> = {};
  loading = false;
  submitting = false;
  errorKey = '';
  errorText = '';
  successKey = '';
  invalidQuestionIds = new Set<string>();

  constructor(
    private surveyService: SurveyService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadForms();
  }

  loadForms(preferredId?: number): void {
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
    this.invalidQuestionIds.delete(questionId);
  }

  answerChanged(questionId: string): void {
    this.invalidQuestionIds.delete(questionId);
    this.errorKey = '';
    this.errorText = '';
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
    this.answers = {};
    if (!form || form.submitted) {
      return;
    }
    for (const question of form.schema.questions) {
      this.answers[question.id] = question.type === 'multiple_choice' ? [] : null;
    }
    this.invalidQuestionIds.clear();
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
