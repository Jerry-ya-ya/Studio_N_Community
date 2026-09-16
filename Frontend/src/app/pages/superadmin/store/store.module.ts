import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';

import { StoreRoutingModule } from './store-routing.module';
import { StoreComponent } from './store.component';


@NgModule({
  declarations: [
    StoreComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    StoreRoutingModule
  ]
})
export class StoreModule { }
