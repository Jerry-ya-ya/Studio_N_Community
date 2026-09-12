import { AuthSessionService } from './auth-session.service';

describe('AuthSessionService', () => {
  beforeEach(() => localStorage.clear());

  it('removes legacy persisted credentials when it starts', () => {
    localStorage.setItem('token', 'legacy-access-token');
    localStorage.setItem('refreshToken', 'legacy-refresh-token');

    const service = new AuthSessionService();

    expect(service.token).toBeNull();
    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
  });

  it('keeps the access token in memory while persisting only display metadata', () => {
    const service = new AuthSessionService();

    service.setSession({
      access_token: 'memory-only-token',
      role: 'admin',
      username: 'jack'
    });

    expect(service.token).toBe('memory-only-token');
    expect(service.isAuthenticated).toBe(true);
    expect(localStorage.getItem('token')).toBeNull();
    expect(localStorage.getItem('role')).toBe('admin');
    expect(localStorage.getItem('username')).toBe('jack');
  });

  it('clears both the in-memory token and session metadata', () => {
    const service = new AuthSessionService();
    service.setSession({ access_token: 'token', role: 'user', username: 'bean' });

    service.clear();

    expect(service.token).toBeNull();
    expect(service.isAuthenticated).toBe(false);
    expect(localStorage.getItem('role')).toBeNull();
    expect(localStorage.getItem('username')).toBeNull();
  });
});
