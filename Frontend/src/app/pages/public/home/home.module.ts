import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslatePipe } from '@ngx-translate/core';

import { HomeRoutingModule } from './home-routing.module';
import { HomeComponent } from './home.component';
import { HomeIntroComponent } from './home-intro/home-intro.component';


@NgModule({
  declarations: [
    HomeComponent
  ],
  imports: [
    CommonModule,
    TranslatePipe,
    HomeIntroComponent,
    HomeRoutingModule
  ]
})
export class HomeModule { }
