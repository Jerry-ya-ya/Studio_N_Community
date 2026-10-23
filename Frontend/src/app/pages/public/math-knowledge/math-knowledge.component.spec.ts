import { ChangeDetectorRef } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { describe, expect, it, vi } from 'vitest';

import { MathGraphDataService } from './math-graph-data.service';
import { MathGraphRendererService } from './math-graph-renderer.service';
import { MathGraphTraversalService } from './math-graph-traversal.service';
import { MathKnowledgeComponent } from './math-knowledge.component';

describe('MathKnowledgeComponent KaTeX rendering', () => {
  it('preserves KaTeX inline metrics for fractions and operator limits', () => {
    const sanitize = vi.fn();
    const bypassSecurityTrustHtml = vi.fn(
      (html: string) => html as unknown as SafeHtml,
    );
    const sanitizer = {
      sanitize,
      bypassSecurityTrustHtml,
    } as unknown as DomSanitizer;
    const component = new MathKnowledgeComponent(
      {} as MathGraphDataService,
      {} as MathGraphTraversalService,
      {} as MathGraphRendererService,
      sanitizer,
      { detectChanges: () => undefined } as unknown as ChangeDetectorRef,
    );

    component.renderFormula("f'(x)=\\lim_{h\\to0}\\frac{f(x+h)-f(x)}{h}");

    expect(sanitize).not.toHaveBeenCalled();
    expect(bypassSecurityTrustHtml).toHaveBeenCalledTimes(1);
    const rendered = bypassSecurityTrustHtml.mock.calls[0]?.[0] ?? '';
    expect(rendered).toContain('class="mfrac"');
    expect(rendered).toContain('class="mop op-limits"');
    expect(rendered).toMatch(/style="[^"]*(?:top|height):/);
  });
});
