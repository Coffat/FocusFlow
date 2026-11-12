import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

interface NavItem {
  path: string;
  label: string;
  icon?: string;
}

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './app-navbar.component.html',
  styleUrl: './app-navbar.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppNavbarComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly currentUser = this.authService.currentUser;

  readonly navItems: NavItem[] = [
    { path: '/dashboard', label: 'Tổng quan' },
    { path: '/roadmaps', label: 'Lộ trình' },
    { path: '/schedule', label: 'Thời khóa biểu' },
    { path: '/tasks', label: 'Hàng đợi Task' },
    { path: '/analytics', label: 'Báo cáo' },
  ];

  readonly userInitials = computed<string>(() => {
    const user = this.currentUser();
    if (!user || !user.fullName) {
      return 'MH';
    }
    const parts = user.fullName.trim().split(/\s+/);
    if (parts.length === 1) {
      return parts[0].slice(0, 2).toUpperCase();
    }
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  });

  readonly userDisplayName = computed<string>(() => {
    const user = this.currentUser();
    return user?.fullName || 'Minh Hoàng';
  });

  readonly userSubtitle = computed<string>(() => {
    const user = this.currentUser();
    if (user && 'role' in user && user.role) {
      return user.role === 'admin' ? 'Quản trị viên' : 'SE K65 • ĐH Bách Khoa';
    }
    return 'SE K65 • ĐH Bách Khoa';
  });

  onSearchTrigger(): void {
    // Navigate to roadmaps or open command palette
    this.router.navigate(['/roadmaps']);
  }
}
