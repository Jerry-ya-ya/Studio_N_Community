import { AfterViewInit, Component, ElementRef, Input, OnDestroy, ViewChild } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-derivative-visualizer',
  standalone: true,
  imports: [MatIconModule],
  templateUrl: './derivative-visualizer.component.html',
  styleUrl: './derivative-visualizer.component.css',
})
export class DerivativeVisualizerComponent implements AfterViewInit, OnDestroy {
  @Input() caption = '';
  @ViewChild('canvas') private canvas?: ElementRef<HTMLCanvasElement>;

  tangentX = -1.3;
  running = true;

  private frameId?: number;
  private previousTime = 0;
  private direction = 1;
  private resizeObserver?: ResizeObserver;

  ngAfterViewInit(): void {
    if (!this.canvas) {
      return;
    }
    this.resizeObserver = new ResizeObserver(() => this.draw());
    this.resizeObserver.observe(this.canvas.nativeElement);
    this.frameId = requestAnimationFrame(time => this.animate(time));
  }

  ngOnDestroy(): void {
    if (this.frameId !== undefined) {
      cancelAnimationFrame(this.frameId);
    }
    this.resizeObserver?.disconnect();
  }

  toggleAnimation(): void {
    this.running = !this.running;
  }

  updateTangent(value: string): void {
    this.tangentX = Number(value);
    this.running = false;
    this.draw();
  }

  private animate(time: number): void {
    const elapsed = Math.min(40, time - this.previousTime);
    this.previousTime = time;
    if (this.running) {
      this.tangentX += this.direction * elapsed * 0.0007;
      if (this.tangentX >= 1.8 || this.tangentX <= -1.8) {
        this.direction *= -1;
        this.tangentX = Math.max(-1.8, Math.min(1.8, this.tangentX));
      }
    }
    this.draw();
    this.frameId = requestAnimationFrame(nextTime => this.animate(nextTime));
  }

  private draw(): void {
    const canvas = this.canvas?.nativeElement;
    if (!canvas) {
      return;
    }
    const bounds = canvas.getBoundingClientRect();
    if (bounds.width <= 0 || bounds.height <= 0) {
      return;
    }

    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(bounds.width * ratio);
    canvas.height = Math.round(bounds.height * ratio);
    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }
    context.setTransform(ratio, 0, 0, ratio, 0, 0);

    const styles = getComputedStyle(canvas);
    const foreground = styles.getPropertyValue('--theme-text').trim() || '#e8f0ea';
    const muted = styles.getPropertyValue('--theme-muted').trim() || '#9fb2a5';
    const accent = styles.getPropertyValue('--theme-primary').trim() || '#7ee2a8';
    const width = bounds.width;
    const height = bounds.height;
    const padding = 30;
    const domain = 2.4;
    const range = 2.3;
    const toCanvasX = (x: number) => padding + ((x + domain) / (domain * 2)) * (width - padding * 2);
    const toCanvasY = (y: number) => height - padding - ((y + 0.4) / (range + 0.4)) * (height - padding * 2);
    const fn = (x: number) => (x * x) / 2;

    context.clearRect(0, 0, width, height);
    context.strokeStyle = muted;
    context.lineWidth = 1;
    context.globalAlpha = 0.45;
    context.beginPath();
    context.moveTo(padding, toCanvasY(0));
    context.lineTo(width - padding, toCanvasY(0));
    context.moveTo(toCanvasX(0), padding);
    context.lineTo(toCanvasX(0), height - padding);
    context.stroke();

    context.globalAlpha = 1;
    context.strokeStyle = foreground;
    context.lineWidth = 2.5;
    context.beginPath();
    for (let index = 0; index <= 160; index += 1) {
      const x = -domain + (index / 160) * domain * 2;
      const canvasX = toCanvasX(x);
      const canvasY = toCanvasY(fn(x));
      if (index === 0) {
        context.moveTo(canvasX, canvasY);
      } else {
        context.lineTo(canvasX, canvasY);
      }
    }
    context.stroke();

    const slope = this.tangentX;
    const pointY = fn(this.tangentX);
    const lineY = (x: number) => pointY + slope * (x - this.tangentX);
    context.strokeStyle = accent;
    context.lineWidth = 3;
    context.beginPath();
    context.moveTo(toCanvasX(-domain), toCanvasY(lineY(-domain)));
    context.lineTo(toCanvasX(domain), toCanvasY(lineY(domain)));
    context.stroke();

    context.fillStyle = accent;
    context.beginPath();
    context.arc(toCanvasX(this.tangentX), toCanvasY(pointY), 6, 0, Math.PI * 2);
    context.fill();
  }
}
