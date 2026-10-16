import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { MathKnowledgeComponent } from './math-knowledge.component';

const routes: Routes = [
  {
    path: '',
    component: MathKnowledgeComponent,
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class MathKnowledgeRoutingModule {}
