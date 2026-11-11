import { afterNextRender, Component, DestroyRef, ElementRef, inject, NgZone, signal, viewChild } from '@angular/core';
import { drawIntro, INTRO_DURATION, stageAt } from './home-intro-plot';

const STORAGE_KEY = 'studio.homeIntro.lastPlayedDate';

function localDateKey(date: Date): string {
  return [date.getFullYear(), date.getMonth() + 1, date.getDate()].join('-');
}

function claimToday(): boolean {
  const today = localDateKey(new Date());
  try {
    if (localStorage.getItem(STORAGE_KEY) === today) {
      return false;
    }
    localStorage.setItem(STORAGE_KEY, today);
    return true;
  } catch {
    return false;
  }
}

@Component({
  selector: 'app-home-intro',
  templateUrl: './home-intro.component.html',
  styleUrl: './home-intro.component.css'
})
export class HomeIntroComponent {
  private readonly dialog = viewChild.required<ElementRef<HTMLDialogElement>>('dialog');
  private readonly plot = viewChild.required<ElementRef<HTMLCanvasElement>>('plot');
  private readonly destroyRef = inject(DestroyRef);
  private readonly zone = inject(NgZone);
  private frame = 0;
  private motionPreference?: MediaQueryList;
  private readonly closeForReducedMotion = (event: MediaQueryListEvent) => {
    if (event.matches) {
      this.finish();
    }
  };

  readonly stages = [
    { name: '學生所在的平面', shortName: '學生', symbol: 'ℝ²', notation: 'X₁, X₂, …, Xₙ ∈ ℝ²' },
    { name: '數學系', shortName: '數學系', symbol: 'A', notation: 'A ⊂ ℝ² · 閉集合' },
    { name: '資訊數學組', shortName: '資訊數學組', symbol: 'B', notation: 'B ⊂ A' },
    { name: '輔仁大學資訊數學', shortName: '輔仁大學', symbol: 'C', notation: 'C ⊂ B · 全台第一資訊數學組' }
  ];
  readonly stageIndex = signal(0);

  constructor() {
    afterNextRender(() => {
      this.motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
      if (this.motionPreference.matches) {
        return;
      }

      const canvas = this.plot().nativeElement;
      const context = canvas.getContext('2d');
      const dialog = this.dialog().nativeElement;
      if (!context || typeof dialog.showModal !== 'function') {
        return;
      }

      const start = () => {
        if (!this.destroyRef.destroyed && !this.motionPreference?.matches && claimToday()) {
          dialog.showModal();
          this.motionPreference?.addEventListener('change', this.closeForReducedMotion);
          this.play(context);
        }
      };

      // Serialize the read and write when multiple tabs open the homepage together.
      if (navigator.locks) {
        void navigator.locks.request(STORAGE_KEY, start).catch(() => start());
      } else {
        start();
      }
    });
    this.destroyRef.onDestroy(() => this.stop());
  }

  finish(): void {
    this.stop();
    this.dialog().nativeElement.close();
  }

  private stop(): void {
    cancelAnimationFrame(this.frame);
    this.motionPreference?.removeEventListener('change', this.closeForReducedMotion);
  }

  private play(context: CanvasRenderingContext2D): void {
    const started = performance.now();
    this.zone.runOutsideAngular(() => {
      const render = (time: number) => {
        const elapsed = Math.max(0, time - started);
        if (elapsed >= INTRO_DURATION) {
          this.zone.run(() => this.finish());
          return;
        }

        const stage = stageAt(elapsed);
        if (stage !== this.stageIndex()) {
          this.zone.run(() => this.stageIndex.set(stage));
        }
        drawIntro(context, elapsed, stage);
        this.frame = requestAnimationFrame(render);
      };
      render(started);
    });
  }
}
