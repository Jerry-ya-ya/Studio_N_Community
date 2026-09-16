import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { TranslatePipe } from '@ngx-translate/core';

import { SpecialAbilitiesRoutingModule } from './special-abilities-routing.module';
import { SpecialAbilitiesComponent } from './special-abilities.component';

@NgModule({
  declarations: [SpecialAbilitiesComponent],
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    TranslatePipe,
    SpecialAbilitiesRoutingModule
  ]
})
export class SpecialAbilitiesModule {}
