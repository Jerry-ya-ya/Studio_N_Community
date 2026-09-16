import { Component, OnDestroy, OnInit } from '@angular/core';
import { finalize, interval, Subscription } from 'rxjs';

import {
  StoreProduct,
  StoreProductService
} from '../../../core/services/store-product.service';
import { environment } from '../../../../environments/environment';

interface RefreshPreferences {
  periodMinutes: number;
  maxRefreshes: number;
  timestamps: number[];
}

const AUTO_REFRESH_MS = 60_000;
const REFRESH_STORAGE_KEY = 'storeRefreshPreferences';
const DEFAULT_PREFERENCES: RefreshPreferences = {
  periodMinutes: 10,
  maxRefreshes: 3,
  timestamps: []
};

@Component({
  selector: 'app-user-store',
  standalone: false,
  templateUrl: './store.component.html',
  styleUrl: './store.component.css'
})
export class StoreComponent implements OnInit, OnDestroy {
  readonly presets: Record<string, string> = {
    bean: 'eco',
    gift: 'redeem',
    ticket: 'confirmation_number'
  };

  products: StoreProduct[] = [];
  preferences = this.readPreferences();
  loading = true;
  refreshing = false;
  purchasingId: number | null = null;
  feedback = '';
  error = '';
  lastUpdatedAt: Date | null = null;
  nextAutoRefreshAt = new Date(Date.now() + AUTO_REFRESH_MS);
  now = new Date();

  private subscriptions = new Subscription();

  constructor(private store: StoreProductService) {}

  ngOnInit(): void {
    this.pruneRefreshHistory();
    this.loadProducts('initial');
    this.subscriptions.add(interval(AUTO_REFRESH_MS).subscribe(() => {
      this.nextAutoRefreshAt = new Date(Date.now() + AUTO_REFRESH_MS);
      this.loadProducts('auto');
    }));
    this.subscriptions.add(interval(1000).subscribe(() => {
      this.now = new Date();
      this.pruneRefreshHistory();
    }));
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  get manualRefreshesRemaining(): number {
    return Math.max(0, this.preferences.maxRefreshes - this.preferences.timestamps.length);
  }

  get canRefreshManually(): boolean {
    return !this.loading && !this.refreshing && this.manualRefreshesRemaining > 0;
  }

  get nextManualRefreshAt(): Date | null {
    if (this.manualRefreshesRemaining > 0 || !this.preferences.timestamps.length) return null;
    return new Date(
      this.preferences.timestamps[0] + this.preferences.periodMinutes * 60_000
    );
  }

  get secondsUntilAutoRefresh(): number {
    return Math.max(0, Math.ceil((this.nextAutoRefreshAt.getTime() - this.now.getTime()) / 1000));
  }

  updatePreferences(): void {
    this.preferences.periodMinutes = this.clampInteger(this.preferences.periodMinutes, 1, 1440);
    this.preferences.maxRefreshes = this.clampInteger(this.preferences.maxRefreshes, 1, 100);
    this.pruneRefreshHistory();
    this.savePreferences();
  }

  refreshManually(): void {
    this.pruneRefreshHistory();
    if (!this.canRefreshManually) return;
    this.preferences.timestamps.push(Date.now());
    this.savePreferences();
    this.loadProducts('manual');
  }

  purchase(product: StoreProduct): void {
    if (this.purchasingId !== null || (product.isLimited && product.stock <= 0)) return;
    this.clearMessages();
    this.purchasingId = product.id;
    this.store.purchase(product.id).pipe(
      finalize(() => this.purchasingId = null)
    ).subscribe({
      next: result => {
        this.feedback = `「${result.purchase.productName}」購買成功`;
        this.replaceProduct(result.product);
        this.loadProducts('purchase');
      },
      error: requestError => {
        this.error = requestError.error?.error || '購買失敗，請稍後再試';
        this.loadProducts('purchase');
      }
    });
  }

  imageUrl(product: StoreProduct): string {
    if (product.imageType !== 'upload') return '';
    if (/^https?:\/\//i.test(product.imageValue)) return product.imageValue;
    const base = environment.apiUrl.startsWith('http')
      ? new URL(environment.apiUrl).origin
      : window.location.origin;
    return `${base}/${product.imageValue.replace(/^\/+/, '')}`;
  }

  presetIcon(value: string): string {
    return this.presets[value] || 'inventory_2';
  }

  private loadProducts(trigger: 'initial' | 'auto' | 'manual' | 'purchase'): void {
    if (this.refreshing) return;
    if (trigger === 'initial') this.loading = true;
    else this.refreshing = true;
    if (trigger !== 'purchase') this.clearMessages();

    this.store.listPublished().pipe(finalize(() => {
      this.loading = false;
      this.refreshing = false;
    })).subscribe({
      next: products => {
        this.products = products;
        this.lastUpdatedAt = new Date();
      },
      error: requestError => {
        this.error = requestError.error?.error || '無法載入商城商品';
      }
    });
  }

  private replaceProduct(saved: StoreProduct): void {
    this.products = this.products.map(product => product.id === saved.id ? saved : product);
  }

  private pruneRefreshHistory(): void {
    const cutoff = Date.now() - this.preferences.periodMinutes * 60_000;
    const active = this.preferences.timestamps.filter(timestamp => timestamp > cutoff);
    if (active.length !== this.preferences.timestamps.length) {
      this.preferences.timestamps = active;
      this.savePreferences();
    }
  }

  private readPreferences(): RefreshPreferences {
    try {
      const stored = JSON.parse(localStorage.getItem(REFRESH_STORAGE_KEY) || 'null');
      if (!stored || !Array.isArray(stored.timestamps)) {
        return { ...DEFAULT_PREFERENCES, timestamps: [] };
      }
      return {
        periodMinutes: this.clampInteger(stored.periodMinutes, 1, 1440),
        maxRefreshes: this.clampInteger(stored.maxRefreshes, 1, 100),
        timestamps: stored.timestamps.filter((value: unknown) => typeof value === 'number')
      };
    } catch {
      return { ...DEFAULT_PREFERENCES, timestamps: [] };
    }
  }

  private savePreferences(): void {
    localStorage.setItem(REFRESH_STORAGE_KEY, JSON.stringify(this.preferences));
  }

  private clampInteger(value: unknown, min: number, max: number): number {
    const number = Number(value);
    return Number.isFinite(number) ? Math.min(max, Math.max(min, Math.round(number))) : min;
  }

  private clearMessages(): void {
    this.feedback = '';
    this.error = '';
  }
}
