import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

import { SpecialAbilitiesComponent } from './special-abilities.component';

const routes: Routes = [{ path: '', component: SpecialAbilitiesComponent }];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class SpecialAbilitiesRoutingModule {}
