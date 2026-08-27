import { Component, OnInit } from '@angular/core';
import { finalize } from 'rxjs';
import { ScheduleBlockDto, ScheduleService } from '../../../core/services/schedule.service';

type ScheduleBlock = ScheduleBlockDto;

@Component({
  selector: 'app-schedule',
  standalone: false,
  templateUrl: './schedule.component.html',
  styleUrl: './schedule.component.css',
})
export class ScheduleComponent implements OnInit {
  readonly columns = [
    'schedule.columns.one',
    'schedule.columns.two',
    'schedule.columns.three',
    'schedule.columns.four',
    'schedule.columns.five'
  ];
  readonly rows = Array.from({ length: 8 }, (_, index) => index + 1);
  readonly storageKey = 'private.schedule.blocks.v1';

  blocks: ScheduleBlock[] = [];
  draggingBlockId: number | null = null;
  trashActive = false;
  loading = false;
  saving = false;
  hasUnsavedChanges = false;
  feedbackMessage = '';
  feedbackType: 'success' | 'error' | '' = '';
  private nextBlockId = 1;

  constructor(private scheduleService: ScheduleService) {}

  ngOnInit() {
    this.loadSchedule();
  }

  addBlock(column: number, startRow: number) {
    if (!this.isSlotAvailable(column, startRow)) {
      return;
    }

    this.blocks = [
      ...this.blocks,
      {
        id: this.nextBlockId++,
        column,
        startRow,
        span: 1,
        title: 'New class'
      }
    ];
    this.markScheduleChanged();
  }

  removeBlock(blockId: number) {
    this.blocks = this.blocks.filter(block => block.id !== blockId);
    this.markScheduleChanged();
  }

  startDrag(event: DragEvent, block: ScheduleBlock) {
    this.draggingBlockId = block.id;
    event.dataTransfer?.setData('text/plain', String(block.id));
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
    }
  }

  finishDrag() {
    this.draggingBlockId = null;
    this.trashActive = false;
  }

  allowDrop(event: DragEvent) {
    if (this.draggingBlockId !== null) {
      event.preventDefault();
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = 'move';
      }
    }
  }

  moveBlockToSlot(event: DragEvent, column: number, startRow: number) {
    event.preventDefault();
    event.stopPropagation();

    const block = this.getDraggedBlock(event);
    if (!block) {
      this.finishDrag();
      return;
    }

    const nextStartRow = Math.min(startRow, this.rows.length - block.span + 1);
    if (!this.isRangeAvailable(column, nextStartRow, block.span, block.id)) {
      this.finishDrag();
      return;
    }

    this.blocks = this.blocks.map(item =>
      item.id === block.id ? { ...item, column, startRow: nextStartRow } : item
    );
    this.markScheduleChanged();
    this.finishDrag();
  }

  showTrashDrop(event: DragEvent) {
    this.allowDrop(event);
    if (this.draggingBlockId !== null) {
      this.trashActive = true;
    }
  }

  hideTrashDrop() {
    this.trashActive = false;
  }

  dropBlockToTrash(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();

    const block = this.getDraggedBlock(event);
    if (block) {
      this.removeBlock(block.id);
    }

    this.finishDrag();
  }

  updateBlockTitle() {
    this.markScheduleChanged();
  }

  changeBlockSpan(block: ScheduleBlock, delta: number) {
    const nextSpan = block.span + delta;
    this.setBlockSpan(block, nextSpan);
  }

  canChangeBlockSpan(block: ScheduleBlock, delta: number) {
    const nextSpan = block.span + delta;
    return nextSpan >= 1 && nextSpan <= this.getMaxSpan(block);
  }

  getBlockStyle(block: ScheduleBlock) {
    return {
      'grid-column': `${block.column + 1}`,
      'grid-row': `${block.startRow} / span ${block.span}`
    };
  }

  getCellStyle(column: number, row: number) {
    return {
      'grid-column': `${column + 1}`,
      'grid-row': `${row}`
    };
  }

  isCoveredByBlock(column: number, row: number) {
    return this.blocks.some(block =>
      block.column === column &&
      row >= block.startRow &&
      row < block.startRow + block.span
    );
  }

  resetSchedule() {
    this.blocks = [];
    this.nextBlockId = this.getNextBlockId();
    this.markScheduleChanged();
  }

  saveSchedule() {
    this.saving = true;
    this.clearFeedback();

    this.scheduleService.saveSchedule(this.blocks)
      .pipe(finalize(() => this.saving = false))
      .subscribe({
        next: response => {
          this.blocks = this.getValidBlocks(response.blocks);
          this.nextBlockId = this.getNextBlockId();
          this.persistLocalDraft();
          this.hasUnsavedChanges = false;
          this.feedbackType = 'success';
          this.feedbackMessage = 'schedule.feedback.saveSuccess';
        },
        error: () => {
          this.feedbackType = 'error';
          this.feedbackMessage = 'schedule.feedback.saveFailed';
        }
      });
  }

  private setBlockSpan(block: ScheduleBlock, span: number) {
    const maxSpan = this.getMaxSpan(block);
    const nextSpan = Math.max(1, Math.min(maxSpan, span));

    if (nextSpan === block.span) {
      return;
    }

    this.blocks = this.blocks.map(item =>
      item.id === block.id ? { ...item, span: nextSpan } : item
    );
    this.markScheduleChanged();
  }

  private getMaxSpan(block: ScheduleBlock) {
    const nextBlock = this.blocks
      .filter(item => item.column === block.column && item.startRow > block.startRow)
      .sort((a, b) => a.startRow - b.startRow)[0];

    const lastAllowedRow = nextBlock ? nextBlock.startRow - 1 : this.rows.length;
    return Math.max(1, lastAllowedRow - block.startRow + 1);
  }

  private isSlotAvailable(column: number, row: number) {
    return !this.isCoveredByBlock(column, row);
  }

  private isRangeAvailable(column: number, startRow: number, span: number, ignoredBlockId?: number) {
    return !this.blocks.some(block =>
      block.id !== ignoredBlockId &&
      block.column === column &&
      startRow < block.startRow + block.span &&
      startRow + span > block.startRow
    );
  }

  private getDraggedBlock(event: DragEvent) {
    const transferId = Number(event.dataTransfer?.getData('text/plain'));
    const blockId = Number.isInteger(transferId) && transferId > 0 ? transferId : this.draggingBlockId;

    if (!blockId) {
      return null;
    }

    return this.blocks.find(block => block.id === blockId) || null;
  }

  private loadSchedule() {
    this.loading = true;
    this.clearFeedback();

    this.scheduleService.getSchedule()
      .pipe(finalize(() => this.loading = false))
      .subscribe({
        next: response => {
          this.blocks = this.getValidBlocks(response.blocks);
          this.nextBlockId = this.getNextBlockId();
          this.persistLocalDraft();
          this.hasUnsavedChanges = false;
        },
        error: () => {
          this.loadLocalDraft();
          this.feedbackType = 'error';
          this.feedbackMessage = 'schedule.feedback.loadFailed';
        }
      });
  }

  private loadLocalDraft() {
    const rawBlocks = localStorage.getItem(this.storageKey);

    if (!rawBlocks) {
      this.blocks = [];
      this.nextBlockId = this.getNextBlockId();
      return;
    }

    try {
      const parsed = JSON.parse(rawBlocks) as ScheduleBlock[];
      this.blocks = this.getValidBlocks(parsed);
    } catch {
      this.blocks = [];
    }

    this.nextBlockId = this.getNextBlockId();
  }

  private markScheduleChanged() {
    this.clearFeedback();
    this.hasUnsavedChanges = true;
    this.persistLocalDraft();
  }

  private persistLocalDraft() {
    localStorage.setItem(this.storageKey, JSON.stringify(this.blocks));
  }

  private clearFeedback() {
    this.feedbackMessage = '';
    this.feedbackType = '';
  }

  private getNextBlockId() {
    return this.blocks.reduce((nextId, block) => Math.max(nextId, block.id + 1), 1);
  }

  private isValidBlock(block: ScheduleBlock) {
    return Number.isInteger(block.id) &&
      Number.isInteger(block.column) &&
      Number.isInteger(block.startRow) &&
      Number.isInteger(block.span) &&
      block.column >= 0 &&
      block.column < this.columns.length &&
      block.startRow >= 1 &&
      block.startRow <= this.rows.length &&
      block.span >= 1 &&
      block.startRow + block.span - 1 <= this.rows.length &&
      typeof block.title === 'string';
  }

  private getValidBlocks(blocks: ScheduleBlock[] | undefined | null) {
    return Array.isArray(blocks) ? blocks.filter(block => this.isValidBlock(block)) : [];
  }
}
