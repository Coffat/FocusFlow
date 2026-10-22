import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: 'learner' | 'admin';
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  // Reactive state using Angular Signals
  readonly currentUser = signal<User | null>(null);
  readonly isAuthenticated = signal<boolean>(false);
  readonly isLoading = signal<boolean>(false);

  login(credentials: { email: string; password: string }): Observable<User> {
    this.isLoading.set(true);
    return this.http.post<User>('/api/v1/auth/login', credentials, { withCredentials: true }).pipe(
      tap({
        next: (user) => {
          this.currentUser.set(user);
          this.isAuthenticated.set(true);
          this.isLoading.set(false);
        },
        error: () => {
          this.isLoading.set(false);
        }
      })
    );
  }

  register(payload: { email: string; password: string; fullName: string }): Observable<User> {
    this.isLoading.set(true);
    return this.http.post<User>('/api/v1/auth/register', payload, { withCredentials: true }).pipe(
      tap({
        next: (user) => {
          this.currentUser.set(user);
          this.isAuthenticated.set(true);
          this.isLoading.set(false);
        },
        error: () => {
          this.isLoading.set(false);
        }
      })
    );
  }

  refreshToken(): Observable<{ status: string }> {
    return this.http.post<{ status: string }>('/api/v1/auth/refresh', {}, { withCredentials: true });
  }

  logout(): void {
    this.http.post('/api/v1/auth/logout', {}, { withCredentials: true }).subscribe({
      next: () => {
        this.clearSession();
      },
      error: () => {
        this.clearSession();
      }
    });
  }

  handleSessionExpired(): void {
    this.clearSession();
    this.router.navigate(['/login'], { queryParams: { expired: '1' } });
  }

  private clearSession(): void {
    this.currentUser.set(null);
    this.isAuthenticated.set(false);
    this.router.navigate(['/login']);
  }
}
