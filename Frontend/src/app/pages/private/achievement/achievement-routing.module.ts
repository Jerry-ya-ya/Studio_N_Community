import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { AchievementComponent } from './achievement.component';

const routes: Routes = [{ path: '', component: AchievementComponent }];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AchievementRoutingModule {}
