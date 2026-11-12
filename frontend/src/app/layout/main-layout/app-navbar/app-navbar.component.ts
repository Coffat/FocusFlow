import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostListener,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  LucideAngularModule,
  LUCIDE_ICONS,
  LucideIconProvider,
  Play,
  Search,
  Bell,
  Settings,
  LogOut,
  Sparkles,
  ChevronDown,
  Menu,
  X,
} from 'lucide-angular';
import { AuthService } from '../../../core/services/auth.service';

export interface NavItem {
  path: string;
  label: string;
}

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, LucideAngularModule],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        Play,
        Search,
        Bell,
        Settings,
        LogOut,
        Sparkles,
        ChevronDown,
        Menu,
        X,
      }),
    },
  ],
  templateUrl: './app-navbar.component.html',
  styleUrl: './app-navbar.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppNavbarComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly elementRef = inject(ElementRef);

  readonly currentUser = this.authService.currentUser;

  readonly isUserMenuOpen = signal<boolean>(false);
  readonly isMobileMenuOpen = signal<boolean>(false);

  readonly navItems: NavItem[] = [
    { path: '/dashboard', label: 'Tổng quan' },
    { path: '/roadmaps', label: 'Roadmap Hub' },
    { path: '/schedule', label: 'Thời khóa biểu' },
    { path: '/tasks', label: 'Hàng đợi Task' },
    { path: '/analytics', label: 'Báo cáo' },
  ];

  readonly userDisplayName = computed<string>(() => {
    const user = this.currentUser();
    return user?.fullName || user?.email?.split('@')[0] || 'Người học';
  });

  readonly userInitials = computed<string>(() => {
    const name = this.userDisplayName().trim();
    if (!name) {
      return 'NH';
    }
    const parts = name.split(/\s+/);
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  });

  readonly userEmail = computed<string>(() => {
    return this.currentUser()?.email || '';
  });

  readonly userTier = computed<string>(() => {
    const tier = this.currentUser()?.tier;
    return (tier || 'FREE').toUpperCase();
  });

  readonly userRole = computed<string>(() => {
    return this.currentUser()?.role || 'user';
  });

  constructor() {
    this.router.events.pipe(takeUntilDestroyed()).subscribe((event) => {
      if (event instanceof NavigationEnd) {
        this.closeUserMenu();
        this.closeMobileMenu();
      }
    });
  }

  toggleUserMenu(): void {
    if (!this.isUserMenuOpen()) {
      this.closeMobileMenu();
    }
    this.isUserMenuOpen.update((v) => !v);
  }

  closeUserMenu(): void {
    this.isUserMenuOpen.set(false);
  }

  toggleMobileMenu(): void {
    if (!this.isMobileMenuOpen()) {
      this.closeUserMenu();
    }
    this.isMobileMenuOpen.update((v) => !v);
  }

  closeMobileMenu(): void {
    this.isMobileMenuOpen.set(false);
  }

  onSearchTrigger(): void {
    this.router.navigate(['/roadmaps']);
  }

  onLogout(): void {
    this.closeUserMenu();
    this.closeMobileMenu();
    this.authService.logout();
    this.router.navigate(['/sign-in']);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as HTMLElement | null;
    if (!target) return;

    if (!target.closest('.user-dropdown-container')) {
      this.closeUserMenu();
    }
    if (!target.closest('.app-navbar')) {
      this.closeMobileMenu();
    }
  }

  @HostListener('document:keydown.escape')
  onEscapePress(): void {
    this.closeUserMenu();
    this.closeMobileMenu();
  }
}
