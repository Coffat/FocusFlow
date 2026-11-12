import { Component, ChangeDetectionStrategy } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-dashboard-empty-state',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="w-full max-w-4xl mx-auto py-12 px-4 sm:px-6 flex flex-col items-center text-center">
      <!-- Architectural Blueprint SVG Illustration -->
      <div class="relative w-64 h-48 sm:w-80 sm:h-56 mb-8 flex items-center justify-center">
        <svg
          class="w-full h-full text-[var(--primary,#005234)]"
          viewBox="0 0 320 220"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <!-- Blueprint Grid Background Pattern -->
          <defs>
            <pattern id="blueprint-grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="currentColor" stroke-opacity="0.08" stroke-width="1" />
            </pattern>
          </defs>
          <rect width="320" height="220" rx="8" fill="url(#blueprint-grid)" />
          <rect x="10" y="10" width="300" height="200" rx="6" stroke="currentColor" stroke-opacity="0.25" stroke-dasharray="4 4" stroke-width="1.5" />

          <!-- Drafting Registration Marks -->
          <line x1="6" y1="110" x2="16" y2="110" stroke="currentColor" stroke-width="1.5" stroke-opacity="0.5" />
          <line x1="304" y1="110" x2="314" y2="110" stroke="currentColor" stroke-width="1.5" stroke-opacity="0.5" />
          <line x1="160" y1="6" x2="160" y2="16" stroke="currentColor" stroke-width="1.5" stroke-opacity="0.5" />
          <line x1="160" y1="204" x2="160" y2="214" stroke="currentColor" stroke-width="1.5" stroke-opacity="0.5" />

          <!-- Roadmap Nodes & Connecting Arcs -->
          <path d="M 60 160 C 100 80, 140 150, 180 90 C 220 30, 240 100, 270 60" fill="none" stroke="#246B4A" stroke-width="2.5" stroke-dasharray="6 4" />

          <!-- Node 1: Origin -->
          <circle cx="60" cy="160" r="14" fill="#FAFAFA" stroke="#246B4A" stroke-width="2" />
          <circle cx="60" cy="160" r="5" fill="#246B4A" />

          <!-- Node 2: Milestone 1 -->
          <rect x="125" y="115" width="26" height="26" rx="4" fill="#FFFFFF" stroke="#005234" stroke-width="2" />
          <line x1="131" y1="128" x2="145" y2="128" stroke="#005234" stroke-width="2" />

          <!-- Node 3: AI Synthesis -->
          <polygon points="180,72 195,98 165,98" fill="#F0DBFF" stroke="#583878" stroke-width="2" />
          <circle cx="180" cy="90" r="3" fill="#583878" />

          <!-- Node 4: Target -->
          <circle cx="270" cy="60" r="16" fill="#FFFFFF" stroke="#246B4A" stroke-width="2" />
          <path d="M 264 60 L 268 64 L 277 55" stroke="#246B4A" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />

          <!-- Dimensional Rulers -->
          <line x1="60" y1="190" x2="270" y2="190" stroke="currentColor" stroke-opacity="0.3" stroke-width="1" />
          <line x1="60" y1="185" x2="60" y2="195" stroke="currentColor" stroke-opacity="0.4" stroke-width="1" />
          <line x1="165" y1="187" x2="165" y2="193" stroke="currentColor" stroke-opacity="0.4" stroke-width="1" />
          <line x1="270" y1="185" x2="270" y2="195" stroke="currentColor" stroke-opacity="0.4" stroke-width="1" />
          <text x="165" y="202" font-family="monospace" font-size="9" fill="currentColor" fill-opacity="0.6" text-anchor="middle">ZIMMERMAN SRL CYCLE: 100% ADAPTIVE</text>
        </svg>
      </div>

      <!-- Headline & Subtitle -->
      <h2 class="text-2xl sm:text-3xl font-bold text-[var(--on-surface,#1b1c1c)] tracking-tight font-serif mb-3">
        Chưa có lộ trình học tập nào
      </h2>
      <p class="text-sm text-[var(--secondary,#5f5e5e)] max-w-lg mx-auto leading-relaxed mb-6 font-sans">
        Hãy bắt đầu bằng cách mô tả mục tiêu học tập hoặc tài liệu bạn muốn chinh phục. AI Harness sẽ phân tích, chia nhỏ thành các cột mốc và tự động tối ưu hóa theo quỹ thời gian của bạn.
      </p>

      <!-- Primary CTA button + Hint -->
      <div class="flex flex-col items-center gap-2 mb-12">
        <a
          routerLink="/roadmaps"
          class="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[var(--primary,#005234)] text-white text-sm font-semibold hover:bg-[var(--primary-container,#246b4a)] transition-all shadow-md group cursor-pointer"
        >
          <span class="material-symbols-outlined text-[18px]">add_circle</span>
          <span>Tạo lộ trình học tập</span>
          <kbd class="ml-1 px-2 py-0.5 text-[11px] font-mono bg-white/20 border border-white/30 rounded font-semibold text-emerald-100">C</kbd>
        </a>
        <span class="text-xs text-[var(--secondary,#5f5e5e)]">
          Mẹo: Bấm phím <kbd class="px-1.5 py-0.5 bg-[var(--surface-container-high,#eae8e7)] rounded text-[11px] font-mono border border-[var(--outline-variant,#bfc9c0)]">C</kbd> trên bàn phím để mở nhanh trình tạo lộ trình
        </span>
      </div>

      <!-- 3 Starter Template Cards -->
      <div class="w-full">
        <div class="text-left mb-4">
          <span class="text-xs font-bold uppercase tracking-wider text-[var(--secondary,#5f5e5e)]">
            Hoặc chọn một lộ trình mẫu phổ biến:
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-left">
          <!-- Template 1: FastAPI & Microservices -->
          <a
            routerLink="/roadmaps"
            [queryParams]="{ goal: 'FastAPI & Microservices' }"
            class="p-5 rounded-lg border border-[var(--outline-variant,#bfc9c0)]/80 bg-[var(--surface-container-lowest,#ffffff)] hover:border-[var(--primary,#005234)] hover:shadow-md transition-all group flex flex-col justify-between"
          >
            <div>
              <div class="flex items-center justify-between mb-3">
                <div class="w-9 h-9 rounded-md bg-emerald-50 text-emerald-800 flex items-center justify-center">
                  <span class="material-symbols-outlined text-[20px]">terminal</span>
                </div>
                <span class="text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                  Backend
                </span>
              </div>
              <h3 class="font-bold text-sm text-[var(--on-surface,#1b1c1c)] group-hover:text-[var(--primary,#005234)] transition-colors mb-1.5">
                FastAPI & Microservices
              </h3>
              <p class="text-xs text-[var(--secondary,#5f5e5e)] leading-relaxed mb-3">
                Domain-Driven Design, SQLAlchemy 2.0 Async, Taskiq background workers và Docker Compose.
              </p>
            </div>
            <div class="pt-3 border-t border-[var(--outline-variant,#bfc9c0)]/40 flex items-center justify-between text-xs text-[var(--secondary,#5f5e5e)]">
              <span>12 tuần • 84 tasks</span>
              <span class="font-semibold text-[var(--primary,#005234)] group-hover:translate-x-0.5 transition-transform inline-flex items-center">
                Chọn &rarr;
              </span>
            </div>
          </a>

          <!-- Template 2: AWS Solutions Architect -->
          <a
            routerLink="/roadmaps"
            [queryParams]="{ goal: 'AWS Solutions Architect' }"
            class="p-5 rounded-lg border border-[var(--outline-variant,#bfc9c0)]/80 bg-[var(--surface-container-lowest,#ffffff)] hover:border-[var(--primary,#005234)] hover:shadow-md transition-all group flex flex-col justify-between"
          >
            <div>
              <div class="flex items-center justify-between mb-3">
                <div class="w-9 h-9 rounded-md bg-blue-50 text-blue-800 flex items-center justify-center">
                  <span class="material-symbols-outlined text-[20px]">cloud</span>
                </div>
                <span class="text-[11px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
                  Cloud Arch
                </span>
              </div>
              <h3 class="font-bold text-sm text-[var(--on-surface,#1b1c1c)] group-hover:text-[var(--primary,#005234)] transition-colors mb-1.5">
                AWS Solutions Architect
              </h3>
              <p class="text-xs text-[var(--secondary,#5f5e5e)] leading-relaxed mb-3">
                Hạ tầng chịu lỗi cao, kiến trúc bảo mật IAM, VPC Peering, RDS Multi-AZ và Serverless Lambda.
              </p>
            </div>
            <div class="pt-3 border-t border-[var(--outline-variant,#bfc9c0)]/40 flex items-center justify-between text-xs text-[var(--secondary,#5f5e5e)]">
              <span>8 tuần • 56 tasks</span>
              <span class="font-semibold text-[var(--primary,#005234)] group-hover:translate-x-0.5 transition-transform inline-flex items-center">
                Chọn &rarr;
              </span>
            </div>
          </a>

          <!-- Template 3: IELTS Academic Band 7.5 -->
          <a
            routerLink="/roadmaps"
            [queryParams]="{ goal: 'IELTS Academic Band 7.5' }"
            class="p-5 rounded-lg border border-[var(--outline-variant,#bfc9c0)]/80 bg-[var(--surface-container-lowest,#ffffff)] hover:border-[var(--primary,#005234)] hover:shadow-md transition-all group flex flex-col justify-between"
          >
            <div>
              <div class="flex items-center justify-between mb-3">
                <div class="w-9 h-9 rounded-md bg-purple-50 text-purple-800 flex items-center justify-center">
                  <span class="material-symbols-outlined text-[20px]">school</span>
                </div>
                <span class="text-[11px] font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-200">
                  Academic
                </span>
              </div>
              <h3 class="font-bold text-sm text-[var(--on-surface,#1b1c1c)] group-hover:text-[var(--primary,#005234)] transition-colors mb-1.5">
                IELTS Academic Band 7.5
              </h3>
              <p class="text-xs text-[var(--secondary,#5f5e5e)] leading-relaxed mb-3">
                Chiến thuật Writing Task 1 & 2 mạch lạc, từ vựng C1/C2 theo chủ đề và Speaking phản xạ tự nhiên.
              </p>
            </div>
            <div class="pt-3 border-t border-[var(--outline-variant,#bfc9c0)]/40 flex items-center justify-between text-xs text-[var(--secondary,#5f5e5e)]">
              <span>10 tuần • 70 tasks</span>
              <span class="font-semibold text-[var(--primary,#005234)] group-hover:translate-x-0.5 transition-transform inline-flex items-center">
                Chọn &rarr;
              </span>
            </div>
          </a>
        </div>
      </div>
    </div>
  `
})
export class DashboardEmptyStateComponent {}
