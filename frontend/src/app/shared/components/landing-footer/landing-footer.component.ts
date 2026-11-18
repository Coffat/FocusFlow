import { ChangeDetectionStrategy, Component, input } from '@angular/core';

export interface FooterLink {
  label: string;
  href: string;
}

@Component({
  selector: 'app-landing-footer',
  standalone: true,
  template: `
    <footer class="w-full border-t border-outline-variant/40 bg-surface">
      <div class="w-full max-w-7xl mx-auto px-6 py-10 flex flex-col md:flex-row justify-between items-center gap-6">
        <!-- Brand & Copyright -->
        <div class="flex flex-col sm:flex-row items-center gap-4 text-center sm:text-left">
          <div class="flex items-center gap-2">
            <div class="w-5 h-5 rounded bg-surface-container flex items-center justify-center text-primary text-[13px]">
              <span class="material-symbols-outlined text-[14px]">all_inclusive</span>
            </div>
            <span class="text-sm font-semibold text-on-surface font-sans">{{ brandName() }}</span>
          </div>
          <span class="hidden sm:inline text-outline-variant/60">|</span>
          <p class="text-xs text-on-surface-variant font-sans">
            {{ copyrightText() }}
          </p>
        </div>

        <!-- Links from Input -->
        <div class="flex flex-wrap items-center justify-center gap-6 text-xs font-sans">
          @for (link of links(); track link.label) {
            <a class="text-on-surface-variant hover:text-on-surface transition-colors" [href]="link.href">
              {{ link.label }}
            </a>
          }
        </div>

        <!-- Engine Status Pill -->
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container-low border border-outline-variant/40 text-xs font-mono text-on-surface-variant">
          <span class="w-2 h-2 rounded-full bg-primary-container"></span>
          <span>{{ statusText() }}</span>
        </div>
      </div>
    </footer>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LandingFooterComponent {
  readonly brandName = input<string>('FocusFlow');
  readonly copyrightText = input<string>('© 2025 FocusFlow Systems Inc. Architectural precision for autonomous intellect.');
  readonly statusText = input<string>('Động cơ Thích ứng: 99.99%');
  readonly links = input<FooterLink[]>([
    { label: 'Trạng thái Hệ thống', href: '#' },
    { label: 'Khung Phương pháp', href: '#' },
    { label: 'Chính sách Quyền riêng tư', href: '#' },
    { label: 'Bảo mật Dữ liệu', href: '#' },
    { label: 'Nhật ký Thay đổi', href: '#' },
  ]);
}
