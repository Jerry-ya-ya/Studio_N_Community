import { Injectable, Injector } from '@angular/core';

import {HttpClient, HttpEvent, HttpInterceptor, HttpHandler, HttpRequest, HttpErrorResponse} from '@angular/common/http';

import { Observable, throwError } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';

import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { environment } from '../../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class AuthInterceptor implements HttpInterceptor {
  private sessionExpiredSnackOpen = false;
  private readonly apiBaseUrl = environment.apiUrl.replace(/\/+$/, '');

  constructor(
    private router: Router,
    private injector: Injector,
    private translate: TranslateService,
    private http: HttpClient
  ) {}
  
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const token = localStorage.getItem('token');
    const isBackendApiRequest = this.isBackendApiRequest(req.url);

    let authReq = req;
    
    if (token && isBackendApiRequest && !this.isRefreshRequest(req.url)) {
      authReq = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`
        }
      });
    }

    return next.handle(authReq).pipe(
      catchError((error: HttpErrorResponse) => {
        if (isBackendApiRequest && error.status === 401 && !this.isLoginRequest(req.url)) {
          if (this.isRefreshRequest(req.url)) {
            this.clearSessionAndRedirect();
            return throwError(() => error);
          }

          return this.refreshAccessToken().pipe(
            switchMap(accessToken => {
              const retryReq = req.clone({
                setHeaders: {
                  Authorization: `Bearer ${accessToken}`
                }
              });
              return next.handle(retryReq);
            }),
            catchError(refreshError => {
              this.clearSessionAndRedirect();
              return throwError(() => refreshError);
            })
          );
        }
        return throwError(() => error);
      })
    );
  }

  private isBackendApiRequest(url: string) {
    return url === this.apiBaseUrl || url.startsWith(`${this.apiBaseUrl}/`) || url.startsWith('/api/');
  }

  private isLoginRequest(url: string) {
    return url.split('?')[0].replace(/\/+$/, '').endsWith('/login');
  }

  private isRefreshRequest(url: string) {
    return url.split('?')[0].replace(/\/+$/, '').endsWith('/refresh');
  }

  private refreshAccessToken(): Observable<string> {
    const refreshToken = localStorage.getItem('refreshToken');

    if (!refreshToken) {
      return throwError(() => new Error('Missing refresh token'));
    }

    return this.http.post<{ access_token: string; role?: string; username?: string }>(
      `${this.apiBaseUrl}/refresh`,
      {},
      {
        headers: {
          Authorization: `Bearer ${refreshToken}`
        }
      }
    ).pipe(
      map(response => {
        localStorage.setItem('token', response.access_token);
        if (response.role) {
          localStorage.setItem('role', response.role);
        }
        if (response.username) {
          localStorage.setItem('username', response.username);
        }
        return response.access_token;
      })
    );
  }

  private clearSessionAndRedirect() {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('role');
    localStorage.removeItem('username');
    this.openSessionExpiredSnack();
    this.router.navigate(['/login']);
  }

  private async openSessionExpiredSnack() {
    if (this.sessionExpiredSnackOpen) {
      return;
    }

    this.sessionExpiredSnackOpen = true;
    const { MatSnackBar } = await import('@angular/material/snack-bar');
    const snackBar = this.injector.get(MatSnackBar);

    snackBar.open(
      this.translate.instant('auth.feedback.sessionExpired'),
      this.translate.instant('login.feedback.dismiss'),
      {
        duration: 4000,
        horizontalPosition: 'right',
        verticalPosition: 'top',
        panelClass: ['studio-snackbar', 'studio-snackbar-error']
      }
    ).afterDismissed().subscribe(() => {
      this.sessionExpiredSnackOpen = false;
    });
  }
}
