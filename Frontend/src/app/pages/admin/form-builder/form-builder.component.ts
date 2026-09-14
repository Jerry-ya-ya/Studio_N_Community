import { ChangeDetectionStrategy, ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

import {
  AdminForm,
  FormBuilderService,
  FormOption,
  FormQuestion,
  FormQuestionType,
  FormSchema
} from '../../../core/services/form-builder.service';


interface FormDraft {
  id: number | null;
  title: string;
  description: string;
  settlementAt: string;
  settled: boolean;
  schema: FormSchema;
  version: number;
  updatedAt: string | null;
}

interface QuestionTypeOption {
  value: FormQuestionType;
  labelKey: string;
}

const CHOICE_TYPES = new Set<FormQuestionType>([
  'single_choice',
  'multiple_choice',
  'dropdown'
]);

@Component({
  selector: 'app-form-builder',
  standalone: false,
  templateUrl: './form-builder.component.html',
  styleUrl: './form-builder.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FormBuilderComponent implements OnInit {
  readonly maxQuestions = 100;
  readonly maxOptions = 50;
  readonly questionTypes: QuestionTypeOption[] = [
    { value: 'short_text', labelKey: 'formBuilder.types.shortText' },
    { value: 'long_text', labelKey: 'formBuilder.types.longText' },
    { value: 'single_choice', labelKey: 'formBuilder.types.singleChoice' },
    { value: 'multiple_choice', labelKey: 'formBuilder.types.multipleChoice' },
    { value: 'dropdown', labelKey: 'formBuilder.types.dropdown' },
    { value: 'number', labelKey: 'formBuilder.types.number' },
    { value: 'date', labelKey: 'formBuilder.types.date' },
    { value: 'boolean', labelKey: 'formBuilder.types.boolean' }
  ];

  forms: AdminForm[] = [];
  draft: FormDraft | null = null;
  loading = false;
  saving = false;
  deleting = false;
  settling = false;
  feedbackKey = '';
  errorKey = '';
  errorText = '';

  constructor(
    private formBuilderService: FormBuilderService,
    private translate: TranslateService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.loadForms();
  }

  loadForms(): void {
    this.loading = true;
    this.clearFeedback();
    this.formBuilderService.listForms().subscribe({
      next: forms => {
        this.forms = forms;
        this.loading = false;
        if (this.draft?.id) {
          const refreshed = forms.find(form => form.id === this.draft?.id);
          if (refreshed) {
            this.draft = this.toDraft(refreshed);
          }
        }
        this.cdr.markForCheck();
      },
      error: error => {
        this.loading = false;
        this.setRequestError(error, 'formBuilder.feedback.loadFailure');
      }
    });
  }

  createNewForm(): void {
    this.clearFeedback();
    this.draft = {
      id: null,
      title: '',
      description: '',
      settlementAt: '',
      settled: false,
      schema: { schemaVersion: 1, questions: [] },
      version: 1,
      updatedAt: null
    };
    this.cdr.markForCheck();
  }

  selectForm(form: AdminForm): void {
    if (this.saving || this.deleting || this.settling) {
      return;
    }
    this.clearFeedback();
    this.draft = this.toDraft(form);
    this.cdr.markForCheck();
  }

  addQuestion(): void {
    if (!this.draft || this.draft.schema.questions.length >= this.maxQuestions) {
      return;
    }
    this.draft.schema.questions.push({
      id: this.makeId('q'),
      type: 'short_text',
      title: '',
      description: '',
      required: false,
      options: []
    });
    this.touchDraft();
  }

  removeQuestion(index: number): void {
    this.draft?.schema.questions.splice(index, 1);
    this.touchDraft();
  }

  moveQuestion(index: number, offset: -1 | 1): void {
    if (!this.draft) {
      return;
    }
    const destination = index + offset;
    const questions = this.draft.schema.questions;
    if (destination < 0 || destination >= questions.length) {
      return;
    }
    [questions[index], questions[destination]] = [questions[destination], questions[index]];
    this.touchDraft();
  }

  onQuestionTypeChange(question: FormQuestion): void {
    question.options = this.isChoiceQuestion(question)
      ? [this.createOption(), this.createOption()]
      : [];
    this.touchDraft();
  }

  addOption(question: FormQuestion): void {
    if (question.options.length >= this.maxOptions) {
      return;
    }
    question.options.push(this.createOption());
    this.touchDraft();
  }

  removeOption(question: FormQuestion, index: number): void {
    if (question.options.length <= 2) {
      return;
    }
    question.options.splice(index, 1);
    this.touchDraft();
  }

  isChoiceQuestion(question: FormQuestion): boolean {
    return CHOICE_TYPES.has(question.type);
  }

  saveForm(): void {
    if (!this.draft || this.saving || this.settling || !this.isDraftValid()) {
      return;
    }

    const payload = {
      title: this.draft.title.trim(),
      description: this.draft.description.trim(),
      settlementAt: this.draft.settlementAt || null,
      schema: this.cloneSchema(this.draft.schema)
    };
    this.saving = true;
    this.clearFeedback();
    const request$ = this.draft.id === null
      ? this.formBuilderService.createForm(payload)
      : this.formBuilderService.updateForm(this.draft.id, {
          ...payload,
          version: this.draft.version
        });

    request$.subscribe({
      next: saved => {
        const existingIndex = this.forms.findIndex(form => form.id === saved.id);
        this.forms = existingIndex < 0
          ? [saved, ...this.forms]
          : this.forms.map(form => form.id === saved.id ? saved : form);
        this.draft = this.toDraft(saved);
        this.saving = false;
        this.feedbackKey = 'formBuilder.feedback.saveSuccess';
        this.cdr.markForCheck();
      },
      error: error => {
        this.saving = false;
        this.setRequestError(
          error,
          error?.status === 409
            ? 'formBuilder.feedback.versionConflict'
            : 'formBuilder.feedback.saveFailure'
        );
      }
    });
  }

  deleteForm(): void {
    if (!this.draft?.id || this.deleting || this.settling) {
      return;
    }
    if (!window.confirm(this.translate.instant('formBuilder.editor.deleteConfirm'))) {
      return;
    }

    const formId = this.draft.id;
    this.deleting = true;
    this.clearFeedback();
    this.formBuilderService.deleteForm(formId).subscribe({
      next: () => {
        this.forms = this.forms.filter(form => form.id !== formId);
        this.draft = null;
        this.deleting = false;
        this.feedbackKey = 'formBuilder.feedback.deleteSuccess';
        this.cdr.markForCheck();
      },
      error: error => {
        this.deleting = false;
        this.setRequestError(error, 'formBuilder.feedback.deleteFailure');
      }
    });
  }

  settleForm(): void {
    if (!this.draft?.id || this.draft.settled || this.settling) {
      return;
    }
    if (!window.confirm(this.translate.instant('formBuilder.editor.settleConfirm'))) {
      return;
    }

    this.settling = true;
    this.clearFeedback();
    this.formBuilderService.settleForm(this.draft.id).subscribe({
      next: settled => {
        this.forms = this.forms.map(form => form.id === settled.id ? settled : form);
        this.draft = this.toDraft(settled);
        this.settling = false;
        this.feedbackKey = 'formBuilder.feedback.settleSuccess';
        this.cdr.markForCheck();
      },
      error: error => {
        this.settling = false;
        this.setRequestError(error, 'formBuilder.feedback.settleFailure');
      }
    });
  }

  trackQuestion(_index: number, question: FormQuestion): string {
    return question.id;
  }

  trackOption(_index: number, option: FormOption): string {
    return option.id;
  }

  private isDraftValid(): boolean {
    if (!this.draft?.title.trim()) {
      this.errorKey = 'formBuilder.feedback.titleRequired';
      this.cdr.markForCheck();
      return false;
    }
    const invalidQuestion = this.draft.schema.questions.some(question => {
      if (!question.title.trim()) {
        return true;
      }
      return this.isChoiceQuestion(question) && (
        question.options.length < 2 || question.options.some(option => !option.label.trim())
      );
    });
    if (invalidQuestion) {
      this.errorKey = 'formBuilder.feedback.questionsInvalid';
      this.cdr.markForCheck();
      return false;
    }
    return true;
  }

  private toDraft(form: AdminForm): FormDraft {
    return {
      id: form.id,
      title: form.title,
      description: form.description,
      settlementAt: form.settlementAt?.slice(0, 16) || '',
      settled: form.settled,
      schema: this.cloneSchema(form.schema),
      version: form.version,
      updatedAt: form.updated_at || null
    };
  }

  private cloneSchema(schema: FormSchema): FormSchema {
    return {
      schemaVersion: 1,
      questions: schema.questions.map(question => ({
        ...question,
        options: question.options.map(option => ({ ...option }))
      }))
    };
  }

  private createOption(): FormOption {
    return { id: this.makeId('o'), label: '' };
  }

  private makeId(prefix: string): string {
    const randomPart = typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID().replaceAll('-', '')
      : `${Date.now()}${Math.random().toString(16).slice(2)}`;
    return `${prefix}_${randomPart}`;
  }

  private touchDraft(): void {
    this.clearFeedback();
    this.cdr.markForCheck();
  }

  private clearFeedback(): void {
    this.feedbackKey = '';
    this.errorKey = '';
    this.errorText = '';
  }

  private setRequestError(error: any, fallbackKey: string): void {
    const serverError = error?.error?.error;
    this.errorText = typeof serverError === 'string' ? serverError : '';
    this.errorKey = this.errorText ? '' : fallbackKey;
    this.cdr.markForCheck();
  }
}
