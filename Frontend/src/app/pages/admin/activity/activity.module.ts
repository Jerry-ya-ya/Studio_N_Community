import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ActivityRoutingModule } from './activity-routing.module';
import { ActivityComponent } from './activity.component';
import { TranslatePipe } from '@ngx-translate/core';


@NgModule({
  declarations: [
    ActivityComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    ActivityRoutingModule,
    TranslatePipe
  ]
})
export class ActivityModule { }
