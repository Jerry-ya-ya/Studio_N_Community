import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';

import { MathKnowledgeDataset } from './math-knowledge.models';

@Injectable()
export class MathGraphDataService {
  private readonly dataset$: Observable<MathKnowledgeDataset>;

  constructor(http: HttpClient) {
    this.dataset$ = http
      .get<MathKnowledgeDataset>('/assets/data/math-knowledge.json')
      .pipe(shareReplay({ bufferSize: 1, refCount: false }));
  }

  load(): Observable<MathKnowledgeDataset> {
    return this.dataset$;
  }
}
