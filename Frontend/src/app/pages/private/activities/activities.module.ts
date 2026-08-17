import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ActivitiesRoutingModule } from './activities-routing.module';
import { ActivitiesComponent } from './activities.component';


@NgModule({
  declarations: [
    ActivitiesComponent
  ],
  imports: [
    CommonModule,
    ActivitiesRoutingModule
  ]
})
export class ActivitiesModule { }
