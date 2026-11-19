import {
  ChangeDetectionStrategy,
  Component,
  HostListener,
  PLATFORM_ID,
  inject,
  input,
  signal,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router, RouterLink } from '@angular/router';

export interface NavLink {
  label: string;
  href: string;
  exact?: boolean;
}

@Component({
  selector: 'app-floating-navbar',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './floating-navbar.component.html',
  styleUrl: './floating-navbar.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FloatingNavbarComponent {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly router = inject(Router);

  readonly brandName = input<string>('FocusFlow');
  readonly navLinks = input<NavLink[]>([
    { label: 'Trang chủ', href: '/', exact: true },
    { label: 'Phương pháp', href: '/#methodology' },
    { label: 'Tính năng', href: '/#capabilities' },
    { label: 'Bảng giá', href: '/pricing' },
    { label: 'Hỏi đáp (FAQ)', href: '/faq' },
  ]);
  readonly isAuthenticated = input<boolean>(false);
  readonly dashboardUrl = input<string>('/dashboard');
  readonly loginUrl = input<string>('/sign-in');
  readonly registerUrl = input<string>('/sign-up');

  readonly mobileMenuOpen = signal<boolean>(false);
  readonly isScrolled = signal<boolean>(
    isPlatformBrowser(this.platformId) && typeof window !== 'undefined' ? window.scrollY > 20 : false
  );

  @HostListener('window:scroll')
  onWindowScroll(): void {
    if (isPlatformBrowser(this.platformId) && typeof window !== 'undefined') {
      this.isScrolled.set(window.scrollY > 20);
    }
  }

  toggleMobileMenu(): void {
    this.mobileMenuOpen.update((v) => !v);
  }

  closeMobileMenu(): void {
    this.mobileMenuOpen.set(false);
  }

  isLinkActive(href: string, exact = false): boolean {
    if (!href.startsWith('/') || href.startsWith('/#')) {
      return false;
    }
    const currentUrl = this.router.url.split('?')[0].split('#')[0];
    const targetPath = href.split('?')[0].split('#')[0];
    if (targetPath === '/') {
      return currentUrl === '/' || currentUrl === '';
    }
    return exact ? currentUrl === targetPath : currentUrl === targetPath || currentUrl.startsWith(targetPath + '/');
  }

  handleAnchorClick(href: string, event: Event): void {
    if (href.startsWith('/#')) {
      const elementId = href.substring(2);
      this.scrollTo(elementId, event);
      return;
    }

    if (href.startsWith('/')) {
      this.closeMobileMenu();
      return;
    }

    if (href.startsWith('#')) {
      const elementId = href.substring(1);
      this.scrollTo(elementId, event);
    }
  }

  scrollTo(elementId: string, event?: Event): void {
    if (event) {
      event.preventDefault();
    }
    this.closeMobileMenu();

    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    const element = document.getElementById(elementId);
    if (element && typeof element.scrollIntoView === 'function') {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      this.router.navigate(['/'], { fragment: elementId }).then(() => {
        setTimeout(() => {
          const target = document.getElementById(elementId);
          if (target && typeof target.scrollIntoView === 'function') {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }, 150);
      });
    }
  }
}
