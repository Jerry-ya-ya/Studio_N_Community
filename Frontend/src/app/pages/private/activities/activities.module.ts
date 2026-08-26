import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslatePipe } from '@ngx-translate/core';

import { ActivitiesRoutingModule } from './activities-routing.module';
import { ActivitiesComponent } from './activities.component';


@NgModule({
  declarations: [
    ActivitiesComponent
  ],
  imports: [
    CommonModule,
    TranslatePipe,
    ActivitiesRoutingModule
  ]
})
export class ActivitiesModule { }
