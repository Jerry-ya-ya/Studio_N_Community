import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { CheckInRoutingModule } from './check-in-routing.module';
import { CheckInComponent } from './check-in.component';
import { TranslatePipe } from '@ngx-translate/core';
import { MatIconModule } from '@angular/material/icon';


@NgModule({
  declarations: [
    CheckInComponent
  ],
  imports: [
    CommonModule,
    CheckInRoutingModule,
    TranslatePipe,
    MatIconModule
  ]
})
export class CheckInModule { }
