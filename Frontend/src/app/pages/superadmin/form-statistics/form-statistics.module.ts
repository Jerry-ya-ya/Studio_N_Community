import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { TranslatePipe } from '@ngx-translate/core';

import { FormStatisticsRoutingModule } from './form-statistics-routing.module';
import { FormStatisticsComponent } from './form-statistics.component';

@NgModule({
  declarations: [FormStatisticsComponent],
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    TranslatePipe,
    FormStatisticsRoutingModule
  ]
})
export class FormStatisticsModule {}
