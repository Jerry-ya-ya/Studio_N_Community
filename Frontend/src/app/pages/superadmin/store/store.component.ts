import { Component, OnDestroy, OnInit } from '@angular/core';
import { finalize, of, switchMap } from 'rxjs';

import {
  StoreProduct,
  StoreProductInput,
  StoreProductService
} from '../../../core/services/store-product.service';
import { environment } from '../../../../environments/environment';

type ProductDraft = StoreProductInput;

const EMPTY_DRAFT: ProductDraft = {
  name: '',
  description: '',
  price: 0,
  stock: 0,
  isLimited: true,
  isPublished: false,
  imageType: 'default',
  imageValue: 'bean'
};

@Component({
  selector: 'app-store',
  standalone: false,
  templateUrl: './store.component.html',
  styleUrl: './store.component.css'
})
export class StoreComponent implements OnInit, OnDestroy {
  readonly presets = [
    { id: 'bean', icon: 'eco', label: '魔豆' },
    { id: 'gift', icon: 'redeem', label: '禮物' },
    { id: 'ticket', icon: 'confirmation_number', label: '票券' }
  ];

  products: StoreProduct[] = [];
  draft: ProductDraft = { ...EMPTY_DRAFT };
  editingId: number | null = null;
  selectedFile: File | null = null;
  editingUsesUpload = false;
  previewUrl = '';
  restockAmounts: Record<number, number> = {};
  loading = true;
  saving = false;
  busyProductId: number | null = null;
  feedback = '';
  error = '';

  constructor(private store: StoreProductService) {}

  ngOnInit(): void {
    this.loadProducts();
  }

  ngOnDestroy(): void {
    this.releasePreview();
  }

  get publishedCount(): number {
    return this.products.filter(product => product.isPublished).length;
  }

  get lowStockCount(): number {
    return this.products.filter(product => product.isLimited && product.stock <= 5).length;
  }

  loadProducts(): void {
    this.loading = true;
    this.store.list().pipe(finalize(() => this.loading = false)).subscribe({
      next: products => this.products = products,
      error: error => this.showError(error, '無法載入商品資料')
    });
  }

  edit(product: StoreProduct): void {
    this.editingId = product.id;
    this.draft = {
      name: product.name,
      description: product.description,
      price: product.price,
      stock: product.stock,
      isLimited: product.isLimited,
      isPublished: product.isPublished,
      imageType: 'default',
      imageValue: product.imageType === 'default' ? product.imageValue : 'bean'
    };
    this.selectedFile = null;
    this.editingUsesUpload = product.imageType === 'upload';
    this.releasePreview();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  resetForm(): void {
    this.editingId = null;
    this.draft = { ...EMPTY_DRAFT };
    this.selectedFile = null;
    this.editingUsesUpload = false;
    this.releasePreview();
  }

  choosePreset(id: string): void {
    this.draft.imageValue = id;
    this.editingUsesUpload = false;
    this.selectedFile = null;
    this.releasePreview();
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] || null;
    this.releasePreview();
    this.selectedFile = file;
    if (file) this.previewUrl = URL.createObjectURL(file);
  }

  save(): void {
    this.clearFeedback();
    if (!this.draft.name.trim()) {
      this.error = '請輸入商品名稱';
      return;
    }
    if (this.draft.price < 0 || this.draft.stock < 0) {
      this.error = '價格與庫存不可小於 0';
      return;
    }
    if (this.draft.isLimited && this.draft.isPublished && this.draft.stock === 0) {
      this.error = '限量商品需有庫存才能上架';
      return;
    }

    this.saving = true;
    const wasCreating = this.editingId === null;
    const updatePayload: Partial<StoreProductInput> = { ...this.draft };
    if (this.editingUsesUpload) {
      delete updatePayload.imageType;
      delete updatePayload.imageValue;
    }
    const request$ = wasCreating
      ? this.store.create(this.draft)
      : this.store.update(this.editingId as number, updatePayload);
    request$.pipe(
      switchMap(product => this.selectedFile
        ? this.store.uploadImage(product.id, this.selectedFile)
        : of(product)),
      finalize(() => this.saving = false)
    ).subscribe({
      next: saved => {
        this.replaceProduct(saved);
        this.feedback = wasCreating ? '商品已建立' : '商品已更新';
        this.resetForm();
      },
      error: error => this.showError(error, '商品儲存失敗')
    });
  }

  togglePublished(product: StoreProduct): void {
    this.clearFeedback();
    this.busyProductId = product.id;
    this.store.update(product.id, { isPublished: !product.isPublished }).pipe(
      finalize(() => this.busyProductId = null)
    ).subscribe({
      next: saved => {
        this.replaceProduct(saved);
        this.feedback = saved.isPublished ? '商品已上架' : '商品已下架';
      },
      error: error => this.showError(error, '無法變更上架狀態')
    });
  }

  restock(product: StoreProduct): void {
    const quantity = Number(this.restockAmounts[product.id]);
    if (!Number.isInteger(quantity) || quantity <= 0) {
      this.error = '請輸入大於 0 的補貨數量';
      return;
    }
    this.clearFeedback();
    this.busyProductId = product.id;
    this.store.restock(product.id, quantity).pipe(
      finalize(() => this.busyProductId = null)
    ).subscribe({
      next: saved => {
        this.replaceProduct(saved);
        this.restockAmounts[product.id] = 0;
        this.feedback = `已為「${product.name}」補充 ${quantity} 件`;
      },
      error: error => this.showError(error, '補貨失敗')
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
    return this.presets.find(preset => preset.id === value)?.icon || 'inventory_2';
  }

  private replaceProduct(saved: StoreProduct): void {
    const exists = this.products.some(product => product.id === saved.id);
    this.products = exists
      ? this.products.map(product => product.id === saved.id ? saved : product)
      : [saved, ...this.products];
  }

  private showError(error: { error?: { error?: string } }, fallback: string): void {
    this.error = error.error?.error || fallback;
  }

  private clearFeedback(): void {
    this.feedback = '';
    this.error = '';
  }

  private releasePreview(): void {
    if (this.previewUrl) {
      URL.revokeObjectURL(this.previewUrl);
      this.previewUrl = '';
    }
  }
}
