import '@angular/compiler';
import { HttpErrorResponse, HttpRequest, HttpResponse } from '@angular/common/http';
import { of, Subject, throwError } from 'rxjs';
import { AuthInterceptor } from './auth-interceptor.service';
import { AuthSessionService } from '../auth-session.service';

describe('AuthInterceptor', () => {
  let authSession: AuthSessionService;

  beforeEach(() => {
    localStorage.clear();
    authSession = new AuthSessionService();
  });

  function createInterceptor(http: { post: ReturnType<typeof vi.fn> }) {
    return new AuthInterceptor(
      { navigate: vi.fn() } as any,
      {} as any,
      { instant: vi.fn((key: string) => key) } as any,
      http as any,
      authSession
    );
  }

  it('adds the in-memory access token only to backend requests', () => {
    authSession.setSession({ access_token: 'access-token' });
    const interceptor = createInterceptor({ post: vi.fn() });
    const handledRequests: HttpRequest<unknown>[] = [];
    const handler = {
      handle: vi.fn((request: HttpRequest<unknown>) => {
        handledRequests.push(request);
        return of(new HttpResponse({ status: 200 }));
      })
    };

    interceptor.intercept(new HttpRequest('GET', '/api/me'), handler).subscribe();
    interceptor.intercept(new HttpRequest('GET', 'https://example.com/image'), handler).subscribe();

    expect(handledRequests[0]?.headers.get('Authorization')).toBe('Bearer access-token');
    expect(handledRequests[0]?.withCredentials).toBe(true);
    expect(handledRequests[1]?.headers.has('Authorization')).toBe(false);
    expect(handledRequests[1]?.withCredentials).toBe(false);
  });

  it('shares one refresh request across simultaneous unauthorized requests', () => {
    const refreshResponse = new Subject<{ access_token: string }>();
    const http = { post: vi.fn(() => refreshResponse.asObservable()) };
    const interceptor = createInterceptor(http);
    const handler = {
      handle: vi.fn((request: HttpRequest<unknown>) => request.headers.has('Authorization')
        ? of(new HttpResponse({ status: 200 }))
        : throwError(() => new HttpErrorResponse({ status: 401 })))
    };

    interceptor.intercept(new HttpRequest('GET', '/api/me'), handler).subscribe();
    interceptor.intercept(new HttpRequest('GET', '/api/todos'), handler).subscribe();

    expect(http.post).toHaveBeenCalledTimes(1);

    refreshResponse.next({ access_token: 'refreshed-token' });
    refreshResponse.complete();

    expect(authSession.token).toBe('refreshed-token');
    expect(handler.handle).toHaveBeenCalledTimes(4);
  });
});
