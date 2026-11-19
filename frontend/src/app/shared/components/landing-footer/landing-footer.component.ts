import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

export interface FooterLink {
  label: string;
  href: string;
}

@Component({
  selector: 'app-landing-footer',
  standalone: true,
  imports: [RouterLink],
  template: `
    <footer class="w-full border-t border-outline-variant/40 bg-surface">
      <div class="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 flex flex-col md:flex-row justify-between items-center gap-6">
        <!-- Brand & Copyright -->
        <div class="flex flex-col sm:flex-row items-center gap-4 text-center sm:text-left">
          <div class="flex items-center gap-2 whitespace-nowrap shrink-0">
            <img src="assets/logo.svg" alt="" width="24" height="24" class="w-5 h-5 shrink-0" />
            <span class="text-sm font-bold font-sans tracking-tight">
              @if (brandName() === 'FocusFlow') {
                <span class="text-on-surface">Focus</span><span class="text-[#205C43]">Flow</span>
              } @else {
                <span class="text-on-surface">{{ brandName() }}</span>
              }
            </span>
          </div>
          <span class="hidden sm:inline text-outline-variant/60">|</span>
          <p class="text-xs text-on-surface-variant font-sans">
            {{ copyrightText() }}
          </p>
        </div>

        <!-- Links from Input -->
        <div class="flex flex-wrap items-center justify-center gap-6 text-xs font-sans">
          @for (link of links(); track link.label) {
            @if (link.href.startsWith('/') && !link.href.startsWith('/#')) {
              <a class="text-on-surface-variant hover:text-on-surface transition-colors whitespace-nowrap" [routerLink]="link.href">
                {{ link.label }}
              </a>
            } @else {
              <a class="text-on-surface-variant hover:text-on-surface transition-colors whitespace-nowrap" [href]="link.href">
                {{ link.label }}
              </a>
            }
          }
        </div>

        <!-- Engine Status Pill -->
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container-low border border-outline-variant/40 text-xs font-mono text-on-surface-variant whitespace-nowrap shrink-0">
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
  readonly copyrightText = input<string>(
    '© 2026 FocusFlow — Hệ thống Điều phối Lộ trình Tự học Thích ứng (SRL Learning Harness).'
  );
  readonly statusText = input<string>('3-Tier Validation Gate • 2-Stage SSE');
  readonly links = input<FooterLink[]>([
    { label: 'Trang chủ', href: '/' },
    { label: 'Phương pháp', href: '/#methodology' },
    { label: 'Tính năng', href: '/#capabilities' },
    { label: 'Bảng giá', href: '/pricing' },
    { label: 'Hỏi đáp (FAQ)', href: '/faq' },
  ]);
}
