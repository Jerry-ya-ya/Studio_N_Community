import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';

import { AchievementRoutingModule } from './achievement-routing.module';
import { AchievementComponent } from './achievement.component';

@NgModule({
  declarations: [AchievementComponent],
  imports: [CommonModule, AchievementRoutingModule, TranslatePipe]
})
export class AchievementModule {}
