import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslatePipe } from '@ngx-translate/core';

import { SurveyRoutingModule } from './survey-routing.module';
import { SurveyComponent } from './survey.component';


@NgModule({
  declarations: [SurveyComponent],
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatSnackBarModule,
    TranslatePipe,
    SurveyRoutingModule
  ]
})
export class SurveyModule {}
