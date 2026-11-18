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
import { RouterLink } from '@angular/router';

export interface NavLink {
  label: string;
  href: string;
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

  readonly brandName = input<string>('FocusFlow');
  readonly navLinks = input<NavLink[]>([
    { label: 'Phương pháp', href: '#methodology' },
    { label: 'Tính năng', href: '#capabilities' },
    { label: 'Kịch bản mẫu', href: '#scenarios' },
    { label: 'Minh chứng', href: '#testimonials' },
  ]);
  readonly isAuthenticated = input<boolean>(false);
  readonly dashboardUrl = input<string>('/dashboard');
  readonly loginUrl = input<string>('/sign-in');
  readonly registerUrl = input<string>('/sign-up');

  readonly mobileMenuOpen = signal<boolean>(false);
  readonly isScrolled = signal<boolean>(false);

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

  handleAnchorClick(href: string, event: Event): void {
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
    const element = document.getElementById(elementId);
    if (element && typeof element.scrollIntoView === 'function') {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
}
