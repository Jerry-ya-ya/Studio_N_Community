import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslatePipe } from '@ngx-translate/core';

import { ProjectRecruitmentRoutingModule } from './project-recruitment-routing.module';
import { ProjectRecruitmentComponent } from './project-recruitment.component';

@NgModule({
  declarations: [
    ProjectRecruitmentComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    MatSnackBarModule,
    ProjectRecruitmentRoutingModule,
    TranslatePipe,
  ]
})
export class ProjectRecruitmentModule { }
