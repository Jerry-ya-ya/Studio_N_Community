import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiService } from './api.service';

export type ProductImageType = 'default' | 'upload';

export interface StoreProduct {
  id: number;
  name: string;
  description: string;
  price: number;
  stock: number;
  isLimited: boolean;
  isPublished: boolean;
  imageType: ProductImageType;
  imageValue: string;
  createdAt: string;
  updatedAt: string;
}

export interface StoreProductInput {
  name: string;
  description: string;
  price: number;
  stock: number;
  isLimited: boolean;
  isPublished: boolean;
  imageType: 'default';
  imageValue: string;
}

export interface StorePurchase {
  id: number;
  productId: number | null;
  productName: string;
  unitPrice: number;
  purchasedAt: string;
}

export interface StorePurchaseResult {
  message: string;
  purchase: StorePurchase;
  product: StoreProduct;
}

@Injectable({ providedIn: 'root' })
export class StoreProductService {
  private readonly endpoint = '/superadmin/store/products';

  constructor(private api: ApiService) {}

  list(): Observable<StoreProduct[]> {
    return this.api.get<StoreProduct[]>(this.endpoint);
  }

  create(product: StoreProductInput): Observable<StoreProduct> {
    return this.api.post<StoreProduct>(this.endpoint, product);
  }

  update(id: number, product: Partial<StoreProductInput>): Observable<StoreProduct> {
    return this.api.put<StoreProduct>(`${this.endpoint}/${id}`, product);
  }

  restock(id: number, quantity: number): Observable<StoreProduct> {
    return this.api.post<StoreProduct>(`${this.endpoint}/${id}/restock`, { quantity });
  }

  uploadImage(id: number, image: File): Observable<StoreProduct> {
    const formData = new FormData();
    formData.append('image', image);
    return this.api.post<StoreProduct>(`${this.endpoint}/${id}/image`, formData);
  }

  listPublished(): Observable<StoreProduct[]> {
    return this.api.get<StoreProduct[]>('/store/products');
  }

  purchase(id: number): Observable<StorePurchaseResult> {
    return this.api.post<StorePurchaseResult>(`/store/products/${id}/purchase`, {});
  }
}
