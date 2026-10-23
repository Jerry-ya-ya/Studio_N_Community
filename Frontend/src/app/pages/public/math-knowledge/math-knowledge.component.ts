import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  OnDestroy,
  OnInit,
  ViewChild,
  ViewContainerRef,
  ElementRef,
} from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { renderToString } from 'katex';
import { Subscription } from 'rxjs';

import { MathGraphDataService } from './math-graph-data.service';
import { MathGraphRendererService } from './math-graph-renderer.service';
import { MathGraphTraversalService } from './math-graph-traversal.service';
import { LocalMathGraph, MathKnowledgeDataset, MathKnowledgeNode } from './math-knowledge.models';

@Component({
  selector: 'app-math-knowledge',
  standalone: false,
  templateUrl: './math-knowledge.component.html',
  styleUrl: './math-knowledge.component.css',
  providers: [
    MathGraphDataService,
    MathGraphTraversalService,
    MathGraphRendererService,
  ],
})
export class MathKnowledgeComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('graphHost') private graphHost?: ElementRef<HTMLElement>;
  @ViewChild('visualizationHost', { read: ViewContainerRef })
  private visualizationHost?: ViewContainerRef;

  dataset?: MathKnowledgeDataset;
  localGraph?: LocalMathGraph;
  selectedNode?: MathKnowledgeNode;
  dependencyDepth = 6;
  applicationDepth = 2;
  detailsExpanded = false;
  loading = true;
  errorMessage = '';
  visualizationLoading = false;

  private viewReady = false;
  private loadSubscription?: Subscription;
  private visualizationVersion = 0;
  private readonly formulaCache = new Map<string, SafeHtml>();

  constructor(
    private dataService: MathGraphDataService,
    private traversalService: MathGraphTraversalService,
    private rendererService: MathGraphRendererService,
    private sanitizer: DomSanitizer,
    private changeDetector: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.loadSubscription = this.dataService.load().subscribe({
      next: dataset => {
        this.dataset = dataset;
        this.loading = false;
        this.focusNode(dataset.defaultCenter);
        this.changeDetector.detectChanges();
      },
      error: () => {
        this.loading = false;
        this.errorMessage = 'mathKnowledge.state.error';
        this.changeDetector.detectChanges();
      },
    });
  }

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.renderGraph();
  }

  ngOnDestroy(): void {
    this.visualizationVersion += 1;
    this.loadSubscription?.unsubscribe();
    this.rendererService.destroy();
  }

  focusNode(nodeId: string): void {
    if (!this.dataset || !this.dataset.nodes.some(node => node.id === nodeId)) {
      return;
    }

    this.selectedNode = this.dataset.nodes.find(node => node.id === nodeId);
    this.detailsExpanded = false;
    this.visualizationVersion += 1;
    this.visualizationHost?.clear();
    this.refreshLocalGraph();
  }

  setDepth(kind: 'dependency' | 'application', value: number | string): void {
    const normalized = Math.min(6, Math.max(0, Number(value) || 0));
    if (kind === 'dependency') {
      this.dependencyDepth = normalized;
    } else {
      this.applicationDepth = normalized;
    }
    this.refreshLocalGraph();
  }

  adjustDepth(kind: 'dependency' | 'application', delta: number): void {
    const current = kind === 'dependency' ? this.dependencyDepth : this.applicationDepth;
    this.setDepth(kind, current + delta);
  }

  fitGraph(): void {
    this.rendererService.fit();
  }

  async toggleDetails(): Promise<void> {
    this.detailsExpanded = !this.detailsExpanded;
    this.visualizationVersion += 1;
    const version = this.visualizationVersion;
    this.visualizationHost?.clear();

    if (!this.detailsExpanded || !this.selectedNode?.visualization) {
      return;
    }

    this.visualizationLoading = true;
    this.changeDetector.detectChanges();

    try {
      const { DerivativeVisualizerComponent } = await import(
        './visualizations/derivative-visualizer.component'
      );
      if (version !== this.visualizationVersion || !this.detailsExpanded) {
        return;
      }
      this.changeDetector.detectChanges();
      const component = this.visualizationHost?.createComponent(DerivativeVisualizerComponent);
      component?.setInput('caption', this.selectedNode.visualization.caption);
    } finally {
      if (version === this.visualizationVersion) {
        this.visualizationLoading = false;
        this.changeDetector.detectChanges();
      }
    }
  }

  renderFormula(latex: string, displayMode = true): SafeHtml {
    const cacheKey = `${displayMode ? 'display' : 'inline'}:${latex}`;
    const cached = this.formulaCache.get(cacheKey);
    if (cached) {
      return cached;
    }

    const rendered = renderToString(latex, {
      displayMode,
      throwOnError: false,
      strict: false,
      trust: false,
    });
    // KaTeX uses inline top/height styles to position fraction rows and
    // operator limits. Angular's HTML sanitizer removes those metrics and
    // collapses the numerator, denominator, and limit subscript together.
    // KaTeX still parses untrusted LaTeX with `trust: false`, so trust only
    // the HTML produced by KaTeX itself instead of sanitizing it a second time.
    const safeFormula = this.sanitizer.bypassSecurityTrustHtml(rendered);
    this.formulaCache.set(cacheKey, safeFormula);
    return safeFormula;
  }

  private refreshLocalGraph(): void {
    if (!this.dataset || !this.selectedNode) {
      return;
    }
    this.localGraph = this.traversalService.createLocalGraph(
      this.dataset,
      this.selectedNode.id,
      this.dependencyDepth,
      this.applicationDepth,
    );
    this.renderGraph();
  }

  private renderGraph(): void {
    if (!this.viewReady || !this.graphHost || !this.localGraph) {
      return;
    }

    this.rendererService.mount(
      this.graphHost.nativeElement,
      this.localGraph,
      nodeId => {
        this.focusNode(nodeId);
        this.changeDetector.detectChanges();
      },
    );
  }
}
