import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { TranslatePipe } from '@ngx-translate/core';

import { MathKnowledgeRoutingModule } from './math-knowledge-routing.module';
import { MathKnowledgeComponent } from './math-knowledge.component';

@NgModule({
  declarations: [MathKnowledgeComponent],
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    TranslatePipe,
    MathKnowledgeRoutingModule,
  ],
})
export class MathKnowledgeModule {}
