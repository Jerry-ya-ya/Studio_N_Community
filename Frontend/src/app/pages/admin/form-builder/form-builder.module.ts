import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { TranslatePipe } from '@ngx-translate/core';

import { FormBuilderRoutingModule } from './form-builder-routing.module';
import { FormBuilderComponent } from './form-builder.component';


@NgModule({
  declarations: [FormBuilderComponent],
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    TranslatePipe,
    FormBuilderRoutingModule
  ]
})
export class FormBuilderModule {}
