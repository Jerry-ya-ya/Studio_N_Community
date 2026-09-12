import { Injectable } from '@angular/core';

export interface AuthSessionResponse {
  access_token: string;
  role?: string;
  username?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthSessionService {
  private accessToken: string | null = null;
  private signedOut = false;

  constructor() {
    // Remove credentials left behind by older frontend versions. Access tokens
    // intentionally live only in this service and disappear when the page closes.
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
  }

  get token(): string | null {
    return this.accessToken;
  }

  get isAuthenticated(): boolean {
    return this.accessToken !== null || (!this.signedOut && this.hasRefreshCookie());
  }

  setSession(response: AuthSessionResponse): void {
    this.accessToken = response.access_token;
    this.signedOut = false;

    if (response.role) {
      localStorage.setItem('role', response.role);
    }
    if (response.username) {
      localStorage.setItem('username', response.username);
    }
  }

  clear(): void {
    this.accessToken = null;
    this.signedOut = true;
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('role');
    localStorage.removeItem('username');
  }

  private hasRefreshCookie(): boolean {
    const prefix = `${encodeURIComponent('csrf_refresh_token')}=`;
    return document.cookie.split('; ').some(item => item.startsWith(prefix));
  }
}
