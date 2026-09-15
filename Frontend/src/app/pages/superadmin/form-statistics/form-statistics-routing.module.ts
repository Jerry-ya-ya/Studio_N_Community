import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { FormStatisticsComponent } from './form-statistics.component';

const routes: Routes = [{ path: '', component: FormStatisticsComponent }];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class FormStatisticsRoutingModule {}
