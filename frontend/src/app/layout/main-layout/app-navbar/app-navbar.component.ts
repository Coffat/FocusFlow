import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  HostListener,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
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
  User,
  Clock,
  Shield,
  CheckCheck,
  AlertTriangle,
  RefreshCw,
} from 'lucide-angular';
import { AuthService } from '../../../core/services/auth.service';
import {
  NotificationItemDTO,
  NotificationService,
} from '../../../core/services/notification.service';

export interface NavItem {
  path: string;
  label: string;
}

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, DatePipe, RouterLink, RouterLinkActive, LucideAngularModule],
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
        User,
        Clock,
        Shield,
        CheckCheck,
        AlertTriangle,
        RefreshCw,
      }),
    },
  ],
  templateUrl: './app-navbar.component.html',
  styleUrl: './app-navbar.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppNavbarComponent {
  private readonly authService = inject(AuthService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly elementRef = inject(ElementRef);
  private readonly destroyRef = inject(DestroyRef);

  readonly currentUser = this.authService.currentUser;
  readonly notifications = this.notificationService.items;
  readonly unreadCount = this.notificationService.unreadCount;
  readonly notificationsLoading = this.notificationService.loading;
  readonly notificationsError = this.notificationService.error;

  readonly isUserMenuOpen = signal<boolean>(false);
  readonly isMobileMenuOpen = signal<boolean>(false);
  readonly isNotificationsOpen = signal<boolean>(false);
  readonly markingAllRead = signal<boolean>(false);
  private lastLoadedUserId: string | null = null;

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
    effect(() => {
      const userId = this.currentUser()?.id ?? null;
      if (userId && userId !== this.lastLoadedUserId) {
        this.lastLoadedUserId = userId;
        this.notificationService.loadNotifications();
      } else if (!userId) {
        this.lastLoadedUserId = null;
      }
    });

    this.router.events.pipe(takeUntilDestroyed()).subscribe((event) => {
      if (event instanceof NavigationEnd) {
        this.closeUserMenu();
        this.closeMobileMenu();
        this.closeNotifications();
      }
    });
  }

  toggleUserMenu(): void {
    if (!this.isUserMenuOpen()) {
      this.closeMobileMenu();
      this.closeNotifications();
    }
    this.isUserMenuOpen.update((v) => !v);
  }

  closeUserMenu(): void {
    this.isUserMenuOpen.set(false);
  }

  toggleMobileMenu(): void {
    if (!this.isMobileMenuOpen()) {
      this.closeUserMenu();
      this.closeNotifications();
    }
    this.isMobileMenuOpen.update((v) => !v);
  }

  closeMobileMenu(): void {
    this.isMobileMenuOpen.set(false);
  }

  toggleNotifications(): void {
    const opening = !this.isNotificationsOpen();
    if (opening) {
      this.closeUserMenu();
      this.closeMobileMenu();
      this.notificationService.loadNotifications();
    }
    this.isNotificationsOpen.set(opening);
  }

  closeNotifications(): void {
    this.isNotificationsOpen.set(false);
  }

  onRetryNotifications(): void {
    this.notificationService.loadNotifications();
  }

  onNotificationClick(item: NotificationItemDTO): void {
    if (!item.is_read) {
      this.notificationService
        .markRead(item.id)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({ error: () => undefined });
    }
    this.closeNotifications();
    if (item.resource_url) {
      void this.router.navigateByUrl(item.resource_url);
    }
  }

  onMarkAllRead(): void {
    if (this.unreadCount() === 0 || this.markingAllRead()) {
      return;
    }
    this.markingAllRead.set(true);
    this.notificationService
      .markAllRead()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.markingAllRead.set(false),
        error: () => this.markingAllRead.set(false),
      });
  }

  onSearchTrigger(): void {
    this.router.navigate(['/roadmaps']);
  }

  onLogout(): void {
    this.closeUserMenu();
    this.closeMobileMenu();
    this.closeNotifications();
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
    if (!target.closest('.notification-dropdown-container')) {
      this.closeNotifications();
    }
    if (!target.closest('.app-navbar')) {
      this.closeMobileMenu();
    }
  }

  @HostListener('document:keydown.escape')
  onEscapePress(): void {
    this.closeUserMenu();
    this.closeMobileMenu();
    this.closeNotifications();
  }
}
