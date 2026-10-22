import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { ButtonDirective } from '../../../shared/ui/button/button.directive';
import { InputDirective } from '../../../shared/ui/input/input.directive';
import { CardComponent, CardHeaderDirective, CardTitleDirective, CardDescriptionDirective } from '../../../shared/ui/card/card.component';

@Component({
  selector: 'app-login-page',
  standalone: true,
  imports: [
    FormsModule,
    ButtonDirective,
    InputDirective,
    CardComponent,
    CardHeaderDirective,
    CardTitleDirective,
    CardDescriptionDirective
  ],
  template: `
    <div class="min-h-[80vh] flex items-center justify-center p-4">
      <app-card class="w-full max-w-md">
        <div appCardHeader class="space-y-1">
          <h2 appCardTitle class="text-2xl font-bold tracking-tight text-center">Đăng nhập FocusFlow</h2>
          <p appCardDescription class="text-center">Nhập thông tin tài khoản để tiếp tục phiên học</p>
        </div>

        <form (ngSubmit)="onSubmit()" class="space-y-4 pt-2">
          <div class="space-y-1.5">
            <label class="text-sm font-medium leading-none" for="email">Email</label>
            <input
              appInput
              id="email"
              type="email"
              placeholder="name@example.com"
              [(ngModel)]="email"
              name="email"
              required
            />
          </div>

          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <label class="text-sm font-medium leading-none" for="password">Mật khẩu</label>
            </div>
            <input
              appInput
              id="password"
              type="password"
              placeholder="••••••••"
              [(ngModel)]="password"
              name="password"
              required
            />
          </div>

          @if (errorMessage()) {
            <div class="p-3 rounded-lg bg-[var(--destructive)]/10 text-[var(--destructive)] text-xs font-medium">
              {{ errorMessage() }}
            </div>
          }

          <button
            appButton
            type="submit"
            class="w-full mt-2"
            [disabled]="authService.isLoading()"
          >
            {{ authService.isLoading() ? 'Đang xác thực...' : 'Đăng nhập' }}
          </button>
        </form>
      </app-card>
    </div>
  `
})
export class LoginPageComponent {
  readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  email = '';
  password = '';
  readonly errorMessage = signal<string | null>(null);

  onSubmit(): void {
    if (!this.email || !this.password) {
      this.errorMessage.set('Vui lòng nhập đầy đủ email và mật khẩu.');
      return;
    }

    this.errorMessage.set(null);
    this.authService.login({ email: this.email, password: this.password }).subscribe({
      next: () => {
        this.router.navigate(['/dashboard']);
      },
      error: () => {
        this.errorMessage.set('Tài khoản hoặc mật khẩu không chính xác.');
      }
    });
  }
}
