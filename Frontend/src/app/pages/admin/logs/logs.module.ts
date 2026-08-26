import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslatePipe } from '@ngx-translate/core';

import { LogsRoutingModule } from './logs-routing.module';
import { LogsComponent } from './logs.component';


@NgModule({
  declarations: [
    LogsComponent
  ],
  imports: [
    CommonModule,
    TranslatePipe,
    LogsRoutingModule
  ]
})
export class LogsModule { }
