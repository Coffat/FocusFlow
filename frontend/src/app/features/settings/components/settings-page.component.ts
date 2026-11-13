import {
  Component,
  ChangeDetectionStrategy,
  inject,
  signal,
  computed,
  OnInit,
  OnDestroy,
} from '@angular/core';
import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Subscription } from 'rxjs';
import {
  LucideAngularModule,
  LUCIDE_ICONS,
  LucideIconProvider,
  Settings,
  Sparkles,
  Clock,
  Calendar,
  Shield,
  AlertTriangle,
  Check,
  Copy,
  Lock,
  Trash2,
  ArrowRight,
  Volume2,
  VolumeX,
  Sun,
  Moon,
  Monitor,
  RefreshCw,
  Zap,
  Download,
  CalendarClock,
  Sliders,
  CheckCircle2,
  RotateCcw,
  ExternalLink,
} from 'lucide-angular';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ToastModule } from 'primeng/toast';
import { SettingsService } from '../services/settings.service';
import { AuthService } from '../../../core/services/auth.service';
import { CalendarIntegrationService } from '../../../core/services/calendar-integration.service';

export type SettingsTab = 'general' | 'ai' | 'calendar' | 'security';

@Component({
  selector: 'app-settings-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    DatePipe,
    DecimalPipe,
    LucideAngularModule,
    ConfirmDialogModule,
    ToastModule,
  ],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        Settings,
        Sparkles,
        Clock,
        Calendar,
        Shield,
        AlertTriangle,
        Check,
        Copy,
        Lock,
        Trash2,
        ArrowRight,
        Volume2,
        VolumeX,
        Sun,
        Moon,
        Monitor,
        RefreshCw,
        Zap,
        Download,
        CalendarClock,
        Sliders,
        CheckCircle2,
        RotateCcw,
        ExternalLink,
      }),
    },
  ],
  template: `
    <div class="min-h-screen bg-[#FBF9F8] text-[#1B1C1C] py-8 px-4 sm:px-6 lg:px-8">
      <div class="max-w-6xl mx-auto space-y-8">

        <!-- Top Editorial Header -->
        <header class="border-b border-[#EAE8E7] pb-6">
          <div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <span class="text-[11px] font-semibold tracking-widest uppercase text-[#246B4A] font-mono">
                Cài Đặt & Quản Trị Hệ Thống
              </span>
              <h1 class="text-3xl sm:text-4xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                Cài Đặt FocusFlow
              </h1>
              <p class="text-sm text-[#656464] mt-1.5 max-w-2xl font-sans leading-relaxed">
                Tùy chỉnh không gian học Pomodoro, giám sát hạn ngạch AI Credits, đồng bộ Google Calendar và quản trị an toàn tài khoản.
              </p>
            </div>
            <div class="flex items-center gap-2">
              <a
                routerLink="/availability"
                class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold bg-white border border-[#EAE8E7] text-[#1B1C1C] hover:text-[#246B4A] hover:border-[#246B4A]/40 hover:bg-[#FBF9F8] transition-colors shadow-2xs no-underline"
              >
                <lucide-icon name="calendar-clock" [size]="13" class="text-[#246B4A]"></lucide-icon>
                <span>Cấu hình Thời Gian Rảnh &rarr;</span>
              </a>
            </div>
          </div>
        </header>

        <!-- 4 Clean Horizontal Tabs Navigation (Swiss Modernism Layout) -->
        <nav
          role="tablist"
          aria-label="Cài đặt FocusFlow"
          class="flex items-center gap-2 p-1.5 bg-white border border-[#EAE8E7] rounded-2xl shadow-xs overflow-x-auto"
        >
          <!-- Tab 1: General -->
          <button
            type="button"
            role="tab"
            id="tab-general"
            data-testid="tab-general"
            aria-controls="panel-general"
            [attr.aria-selected]="activeTab() === 'general'"
            [attr.tabindex]="activeTab() === 'general' ? 0 : -1"
            (keydown)="onTabKeydown($event, 'general')"
            (click)="setTab('general')"
            class="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer shrink-0"
            [ngClass]="{
              'bg-[#246B4A] text-white shadow-xs': activeTab() === 'general',
              'text-[#656464] hover:text-[#1B1C1C] hover:bg-[#FBF9F8]': activeTab() !== 'general'
            }"
          >
            <lucide-icon name="clock" [size]="15"></lucide-icon>
            <span>Chung & Không gian học</span>
          </button>

          <!-- Tab 2: AI -->
          <button
            type="button"
            role="tab"
            id="tab-ai"
            data-testid="tab-ai"
            aria-controls="panel-ai"
            [attr.aria-selected]="activeTab() === 'ai'"
            [attr.tabindex]="activeTab() === 'ai' ? 0 : -1"
            (keydown)="onTabKeydown($event, 'ai')"
            (click)="setTab('ai')"
            class="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer shrink-0"
            [ngClass]="{
              'bg-[#246B4A] text-white shadow-xs': activeTab() === 'ai',
              'text-[#656464] hover:text-[#1B1C1C] hover:bg-[#FBF9F8]': activeTab() !== 'ai'
            }"
          >
            <lucide-icon name="sparkles" [size]="15"></lucide-icon>
            <span>AI & Hạn ngạch</span>
          </button>

          <!-- Tab 3: Calendar -->
          <button
            type="button"
            role="tab"
            id="tab-calendar"
            data-testid="tab-calendar"
            aria-controls="panel-calendar"
            [attr.aria-selected]="activeTab() === 'calendar'"
            [attr.tabindex]="activeTab() === 'calendar' ? 0 : -1"
            (keydown)="onTabKeydown($event, 'calendar')"
            (click)="setTab('calendar')"
            class="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer shrink-0"
            [ngClass]="{
              'bg-[#246B4A] text-white shadow-xs': activeTab() === 'calendar',
              'text-[#656464] hover:text-[#1B1C1C] hover:bg-[#FBF9F8]': activeTab() !== 'calendar'
            }"
          >
            <lucide-icon name="calendar" [size]="15"></lucide-icon>
            <span>Lịch & Tích hợp</span>
          </button>

          <!-- Tab 4: Security -->
          <button
            type="button"
            role="tab"
            id="tab-security"
            data-testid="tab-security"
            aria-controls="panel-security"
            [attr.aria-selected]="activeTab() === 'security'"
            [attr.tabindex]="activeTab() === 'security' ? 0 : -1"
            (keydown)="onTabKeydown($event, 'security')"
            (click)="setTab('security')"
            class="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer shrink-0"
            [ngClass]="{
              'bg-[#246B4A] text-white shadow-xs': activeTab() === 'security',
              'text-[#656464] hover:text-[#1B1C1C] hover:bg-[#FBF9F8]': activeTab() !== 'security'
            }"
          >
            <lucide-icon name="shield" [size]="15"></lucide-icon>
            <span>Tài khoản & Bảo mật</span>
          </button>
        </nav>

        <!-- Main Tab Panels -->
        <main class="space-y-6">

          <!-- ================= TAB 1: CHUNG & KHÔNG GIAN HỌC ================= -->
          @if (activeTab() === 'general') {
            <div role="tabpanel" id="panel-general" aria-labelledby="tab-general" class="space-y-6">

              <!-- Pomodoro Workspace Preferences Card -->
              <section class="bg-white rounded-2xl border border-[#EAE8E7] p-6 sm:p-8 shadow-xs space-y-6">
                <div class="border-b border-[#EAE8E7] pb-4">
                  <span class="text-[11px] font-mono uppercase tracking-widest text-[#246B4A] font-semibold">
                    Không Gian Tập Trung
                  </span>
                  <h2 class="text-xl sm:text-2xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                    Thời Lượng Pomodoro & Phiên Học
                  </h2>
                  <p class="text-xs sm:text-sm text-[#656464] mt-1">
                    Thiết lập chu kỳ tập trung phù hợp với khả năng duy trì chú ý và mục tiêu học tập của bạn.
                  </p>
                </div>

                <div class="space-y-6">
                  <!-- Focus Duration Selector: 25m, 45m, 90m -->
                  <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] font-mono mb-2">
                      Thời lượng phiên tập trung (Focus Duration)
                    </label>
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      @for (dur of [25, 45, 90]; track dur) {
                        <button
                          type="button"
                          [attr.data-testid]="'pomodoro-dur-' + dur"
                          [attr.aria-pressed]="preferences().defaultPomodoroDuration === dur"
                          (click)="updatePreference('defaultPomodoroDuration', dur)"
                          class="p-4 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between"
                          [ngClass]="{
                            'border-[#246B4A] bg-emerald-50/50 text-[#1B1C1C] shadow-xs ring-1 ring-[#246B4A]': preferences().defaultPomodoroDuration === dur,
                            'border-[#EAE8E7] bg-white text-[#1B1C1C] hover:border-neutral-400': preferences().defaultPomodoroDuration !== dur
                          }"
                        >
                          <div class="flex items-center justify-between">
                            <span class="text-xl font-bold font-serif">{{ dur }} phút</span>
                            @if (preferences().defaultPomodoroDuration === dur) {
                              <span class="w-5 h-5 rounded-full bg-[#246B4A] text-white flex items-center justify-center">
                                <lucide-icon name="check" [size]="12"></lucide-icon>
                              </span>
                            }
                          </div>
                          <span class="text-xs text-[#656464] mt-2 block font-sans">
                            {{ dur === 25 ? 'Tiêu chuẩn Pomodoro kinh điển' : dur === 45 ? 'Tối ưu hóa tập trung cao độ' : 'Phiên học sâu chuyên đề (Deep Work)' }}
                          </span>
                        </button>
                      }
                    </div>
                  </div>

                  <!-- Break Durations -->
                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                    <!-- Short Break -->
                    <div class="p-4 rounded-xl border border-[#EAE8E7] bg-[#FBF9F8] space-y-2">
                      <label class="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] font-mono">
                        Giải lao ngắn (Short Break)
                      </label>
                      <div class="grid grid-cols-2 gap-2">
                        @for (sDur of [5, 10]; track sDur) {
                          <button
                            type="button"
                            (click)="updatePreference('shortBreakDuration', sDur)"
                            class="py-2.5 px-3 rounded-lg border text-center text-xs font-mono font-medium transition-colors cursor-pointer"
                            [ngClass]="{
                              'bg-[#246B4A] text-white border-[#246B4A] shadow-xs': preferences().shortBreakDuration === sDur,
                              'bg-white text-[#1B1C1C] border-[#EAE8E7] hover:border-neutral-400': preferences().shortBreakDuration !== sDur
                            }"
                          >
                            {{ sDur }} phút
                          </button>
                        }
                      </div>
                    </div>

                    <!-- Long Break -->
                    <div class="p-4 rounded-xl border border-[#EAE8E7] bg-[#FBF9F8] space-y-2">
                      <label class="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] font-mono">
                        Giải lao dài (Long Break)
                      </label>
                      <div class="grid grid-cols-2 gap-2">
                        @for (lDur of [15, 30]; track lDur) {
                          <button
                            type="button"
                            (click)="updatePreference('longBreakDuration', lDur)"
                            class="py-2.5 px-3 rounded-lg border text-center text-xs font-mono font-medium transition-colors cursor-pointer"
                            [ngClass]="{
                              'bg-[#246B4A] text-white border-[#246B4A] shadow-xs': preferences().longBreakDuration === lDur,
                              'bg-white text-[#1B1C1C] border-[#EAE8E7] hover:border-neutral-400': preferences().longBreakDuration !== lDur
                            }"
                          >
                            {{ lDur }} phút
                          </button>
                        }
                      </div>
                    </div>
                  </div>

                  <!-- Audio Chime Toggle -->
                  <div class="flex items-center justify-between p-4 rounded-xl border border-[#EAE8E7] bg-[#FBF9F8]">
                    <div class="space-y-0.5">
                      <div class="flex items-center gap-2 text-sm font-semibold text-[#1B1C1C]">
                        <lucide-icon [name]="preferences().soundEnabled ? 'volume-2' : 'volume-x'" [size]="16" class="text-[#246B4A]"></lucide-icon>
                        <span>Âm thanh chuông báo chu kỳ</span>
                      </div>
                      <p class="text-xs text-[#656464]">
                        Phát âm thanh nhẹ nhàng (Tibetan bell) khi kết thúc phiên học hoặc hết giờ nghỉ.
                      </p>
                    </div>
                    <button
                      type="button"
                      (click)="updatePreference('soundEnabled', !preferences().soundEnabled)"
                      class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer"
                      [ngClass]="preferences().soundEnabled ? 'bg-[#246B4A]' : 'bg-neutral-300'"
                      role="switch"
                      [attr.aria-checked]="preferences().soundEnabled"
                    >
                      <span
                        class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-xs"
                        [ngClass]="preferences().soundEnabled ? 'translate-x-6' : 'translate-x-1'"
                      ></span>
                    </button>
                  </div>

                  <!-- Theme Selection (No Black #111111 Buttons) -->
                  <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] font-mono mb-2">
                      Giao diện hiển thị (Theme)
                    </label>
                    <div class="grid grid-cols-3 gap-3">
                      <button
                        type="button"
                        data-testid="theme-light"
                        [attr.aria-pressed]="preferences().theme === 'light'"
                        (click)="updatePreference('theme', 'light')"
                        class="flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-medium transition-all cursor-pointer"
                        [ngClass]="{
                          'border-[#246B4A] bg-emerald-50/50 text-[#246B4A] font-bold ring-1 ring-[#246B4A]': preferences().theme === 'light',
                          'border-[#EAE8E7] bg-white text-[#1B1C1C] hover:border-neutral-400': preferences().theme !== 'light'
                        }"
                      >
                        <lucide-icon name="sun" [size]="14"></lucide-icon>
                        <span>Sáng (Light)</span>
                      </button>

                      <button
                        type="button"
                        data-testid="theme-dark"
                        [attr.aria-pressed]="preferences().theme === 'dark'"
                        (click)="updatePreference('theme', 'dark')"
                        class="flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-medium transition-all cursor-pointer"
                        [ngClass]="{
                          'border-[#246B4A] bg-emerald-50/50 text-[#246B4A] font-bold ring-1 ring-[#246B4A]': preferences().theme === 'dark',
                          'border-[#EAE8E7] bg-white text-[#1B1C1C] hover:border-neutral-400': preferences().theme !== 'dark'
                        }"
                      >
                        <lucide-icon name="moon" [size]="14"></lucide-icon>
                        <span>Tối (Dark)</span>
                      </button>

                      <button
                        type="button"
                        data-testid="theme-system"
                        [attr.aria-pressed]="preferences().theme === 'system'"
                        (click)="updatePreference('theme', 'system')"
                        class="flex items-center justify-center gap-2 p-3 rounded-xl border text-xs font-medium transition-all cursor-pointer"
                        [ngClass]="{
                          'border-[#246B4A] bg-emerald-50/50 text-[#246B4A] font-bold ring-1 ring-[#246B4A]': preferences().theme === 'system',
                          'border-[#EAE8E7] bg-white text-[#1B1C1C] hover:border-neutral-400': preferences().theme !== 'system'
                        }"
                      >
                        <lucide-icon name="monitor" [size]="14"></lucide-icon>
                        <span>Hệ thống</span>
                      </button>
                    </div>
                  </div>
                </div>
              </section>

            </div>
          }

          <!-- ================= TAB 2: AI & HẠN NGẠCH ================= -->
          @if (activeTab() === 'ai') {
            <div role="tabpanel" id="panel-ai" aria-labelledby="tab-ai" class="space-y-6">

              <section class="bg-white rounded-2xl border border-[#EAE8E7] p-6 sm:p-8 shadow-xs space-y-6">
                <!-- Header with Tier Badge and Refresh Button -->
                <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[#EAE8E7] pb-4">
                  <div>
                    <div class="flex items-center gap-2.5">
                      <span class="text-[11px] font-mono uppercase tracking-widest text-[#246B4A] font-semibold">
                        Tài Nguyên & Định Mức
                      </span>
                      <span
                        class="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold tracking-wide uppercase border"
                        [ngClass]="{
                          'bg-emerald-50 text-[#246B4A] border-emerald-200': userTier() === 'PRO' || userTier() === 'PREMIUM',
                          'bg-neutral-100 text-[#555555] border-neutral-200': userTier() !== 'PRO' && userTier() !== 'PREMIUM'
                        }"
                      >
                        Gói {{ userTier() }}
                      </span>
                    </div>
                    <h2 class="text-xl sm:text-2xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                      Hạn Ngạch Trí Tuệ Nhân Tạo (AI Credits)
                    </h2>
                    <p class="text-xs sm:text-sm text-[#656464] mt-1">
                      Bảo toàn hạn ngạch 2 pha (Reserve/Commit) đảm bảo tác vụ phân rã lộ trình và gợi ý học tập luôn minh bạch.
                    </p>
                  </div>

                  <button
                    type="button"
                    (click)="reloadQuota()"
                    class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-mono font-medium border border-[#EAE8E7] bg-[#FBF9F8] hover:bg-neutral-100 text-[#1B1C1C] transition-colors self-start sm:self-auto cursor-pointer"
                    title="Làm mới số liệu hạn ngạch"
                  >
                    <lucide-icon name="refresh-cw" [size]="13"></lucide-icon>
                    <span>Cập nhật</span>
                  </button>
                </div>

                <!-- Progress Bar -->
                <div class="space-y-2">
                  <div class="flex justify-between items-center text-xs font-mono">
                    <span class="text-[#656464]">Tiến độ sử dụng chu kỳ hiện tại</span>
                    <span class="font-bold text-[#1B1C1C]">
                      {{ quotaUsagePercent() | number: '1.0-0' }}% đã sử dụng
                    </span>
                  </div>
                  <div class="w-full h-3 rounded-full bg-neutral-100 border border-[#EAE8E7] overflow-hidden p-0.5">
                    <div
                      class="h-full rounded-full bg-[#246B4A] transition-all duration-500"
                      [style.width.%]="quotaUsagePercent()"
                    ></div>
                  </div>
                </div>

                <!-- 4-Box Telemetry Grid -->
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div class="p-4 rounded-xl border border-[#EAE8E7] bg-[#FBF9F8] space-y-1">
                    <span class="text-[10px] font-mono font-semibold uppercase tracking-wider text-[#656464] block">Đã cam kết</span>
                    <div class="text-2xl font-bold font-serif text-[#1B1C1C]">
                      {{ quota()?.used_calls ?? preferences().aiCreditsUsed }}
                    </div>
                    <span class="text-[11px] text-[#656464] block font-mono">lượt gọi AI</span>
                  </div>

                  <div class="p-4 rounded-xl border border-[#EAE8E7] bg-[#FBF9F8] space-y-1">
                    <span class="text-[10px] font-mono font-semibold uppercase tracking-wider text-[#656464] block">Đang giữ chỗ</span>
                    <div class="text-2xl font-bold font-serif text-amber-600">
                      {{ quota()?.reserved_calls ?? 0 }}
                    </div>
                    <span class="text-[11px] text-[#656464] block font-mono">đang xử lý</span>
                  </div>

                  <div class="p-4 rounded-xl border border-[#EAE8E7] bg-[#FBF9F8] space-y-1">
                    <span class="text-[10px] font-mono font-semibold uppercase tracking-wider text-[#656464] block">Còn khả dụng</span>
                    <div class="text-2xl font-bold font-serif text-[#246B4A]">
                      {{ quota()?.remaining_calls ?? (preferences().aiCreditsLimit! - preferences().aiCreditsUsed!) }}
                    </div>
                    <span class="text-[11px] text-[#656464] block font-mono">lượt khả dụng</span>
                  </div>

                  <div class="p-4 rounded-xl border border-[#EAE8E7] bg-[#FBF9F8] space-y-1">
                    <span class="text-[10px] font-mono font-semibold uppercase tracking-wider text-[#656464] block">Tokens tiêu thụ</span>
                    <div class="text-2xl font-bold font-serif text-[#1B1C1C]">
                      {{ (quota()?.tokens_consumed ?? 3450) | number }}
                    </div>
                    <span class="text-[11px] text-[#656464] block font-mono">LLM tokens</span>
                  </div>
                </div>

                <!-- Cycle Details & Upgrade Action -->
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-4 border-t border-[#EAE8E7]">
                  <div class="text-xs text-[#656464] font-mono">
                    <span>Ngày làm mới hạn ngạch chu kỳ: </span>
                    <strong class="text-[#1B1C1C]">{{ (quota()?.cycle_end || defaultCycleEnd) | date: 'dd/MM/yyyy' }}</strong>
                    <span class="block text-[11px] text-neutral-400 mt-0.5">
                      Định mức sẽ tự động được phục hồi đầy đủ vào đầu chu kỳ tiếp theo.
                    </span>
                  </div>

                  <button
                    type="button"
                    (click)="onUpgradePlan()"
                    class="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full text-xs font-semibold text-white bg-[#246B4A] hover:bg-[#1B5338] transition-colors shadow-2xs cursor-pointer self-start sm:self-auto"
                  >
                    <lucide-icon name="sparkles" [size]="13" class="text-amber-300"></lucide-icon>
                    <span>Nâng cấp gói PRO / PREMIUM</span>
                  </button>
                </div>
              </section>

            </div>
          }

          <!-- ================= TAB 3: LỊCH & TÍCH HỢP ================= -->
          @if (activeTab() === 'calendar') {
            <div role="tabpanel" id="panel-calendar" aria-labelledby="tab-calendar" class="space-y-6">

              <!-- Quick Link Card to /availability -->
              <div class="p-5 rounded-2xl border border-emerald-200 bg-emerald-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs">
                <div class="space-y-1">
                  <div class="flex items-center gap-2">
                    <span class="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-[#246B4A] text-white">
                      Cấu hình quỹ giờ
                    </span>
                    <h3 class="text-sm font-bold font-serif text-[#1B1C1C]">
                      Quản Lý Thời Gian Rảnh Lai (Mode A & Mode B)
                    </h3>
                  </div>
                  <p class="text-xs text-[#656464] max-w-xl">
                    Chuyển đổi giữa Mode A (phân bổ linh hoạt theo mục tiêu tuần) và Mode B (chọn nhanh các ca Sáng, Chiều, Tối). FocusFlow lập lịch học tự động theo cấu hình này.
                  </p>
                </div>
                <a
                  routerLink="/availability"
                  class="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold text-white bg-[#246B4A] hover:bg-[#1B5338] transition-colors shadow-2xs whitespace-nowrap no-underline shrink-0"
                >
                  <span>Mở trang Lịch Rảnh &rarr;</span>
                </a>
              </div>

              <!-- Google Calendar 1-Click OAuth Integration Card -->
              <section class="bg-white rounded-2xl border border-[#EAE8E7] p-6 sm:p-8 shadow-xs space-y-6">
                <div class="border-b border-[#EAE8E7] pb-4">
                  <span class="text-[11px] font-mono uppercase tracking-widest text-[#246B4A] font-semibold">
                    Đồng Bộ Tự Động 2 Chiều
                  </span>
                  <h2 class="text-xl sm:text-2xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                    Google Calendar 1-Click
                  </h2>
                  <p class="text-xs sm:text-sm text-[#656464] mt-1">
                    Liên kết tài khoản Google để đưa lịch học FocusFlow vào Google Calendar và bảo vệ các cuộc hẹn riêng của bạn khỏi xung đột.
                  </p>
                </div>

                @if (!calendarService.isConnected()) {
                  <!-- Disconnected State: 1-Click Connect Banner -->
                  <div class="p-6 rounded-2xl border border-[#EAE8E7] bg-gradient-to-br from-white to-[#FBF9F8] flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-2xs">
                    <div class="flex items-start gap-4">
                      <div class="w-12 h-12 rounded-xl bg-white border border-[#EAE8E7] shadow-2xs flex items-center justify-center shrink-0">
                        <svg class="w-6 h-6" viewBox="0 0 24 24">
                          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                        </svg>
                      </div>
                      <div>
                        <h3 class="text-sm font-bold text-[#1B1C1C]">Chưa kết nối Google Calendar</h3>
                        <p class="text-xs text-[#656464] mt-1 max-w-lg">
                          Cấp quyền qua tài khoản Google một lần duy nhất. FocusFlow tự động tạo lịch chuyên biệt "FocusFlow Study Schedule" trên Google Calendar.
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      (click)="onConnectGoogleCalendar()"
                      [disabled]="calendarService.isLoading()"
                      class="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-full text-xs font-semibold text-white bg-[#1A73E8] hover:bg-[#1557B0] transition-colors shadow-2xs whitespace-nowrap cursor-pointer shrink-0 disabled:opacity-50"
                    >
                      <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20a2 2 0 0 0 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V10h14v10zM9 14H7v-2h2v2zm4 0h-2v-2h2v2zm4 0h-2v-2h2v2zm-8 4H7v-2h2v2zm4 0h-2v-2h2v2zm4 0h-2v-2h2v2z"/>
                      </svg>
                      <span>{{ calendarService.isLoading() ? 'Đang chuẩn bị...' : 'Kết nối Google Calendar' }}</span>
                    </button>
                  </div>
                } @else {
                  <!-- Connected State -->
                  <div class="p-5 rounded-2xl border border-emerald-200 bg-emerald-50/40 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs">
                    <div class="flex items-start gap-4">
                      <div class="w-12 h-12 rounded-xl bg-white border border-emerald-200 shadow-2xs flex items-center justify-center shrink-0">
                        <lucide-icon name="check" [size]="22" class="text-[#246B4A]"></lucide-icon>
                      </div>
                      <div class="space-y-1">
                        <div class="flex items-center gap-2">
                          <h3 class="text-sm font-bold text-[#1B1C1C]">Google Calendar: Đang hoạt động</h3>
                          <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold tracking-wide uppercase bg-emerald-100 text-[#246B4A] border border-emerald-200">
                            Đã kết nối
                          </span>
                        </div>
                        <p class="text-xs text-[#656464]">
                          Lịch học FocusFlow và Google Calendar đang được đồng bộ tự động 2 chiều.
                          @if (calendarService.connection()?.last_synced_at) {
                            <span class="ml-1 text-[11px] font-mono text-[#246B4A]">
                              (Lần đồng bộ gần nhất: {{ calendarService.connection()?.last_synced_at | date:'HH:mm dd/MM/yyyy' }})
                            </span>
                          }
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      (click)="onDisconnectGoogleCalendar()"
                      [disabled]="calendarService.isLoading()"
                      class="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-full border border-red-200 bg-white hover:bg-red-50 text-xs font-semibold text-[#BA1A1A] transition-colors shadow-2xs cursor-pointer shrink-0 disabled:opacity-50"
                    >
                      <lucide-icon name="trash-2" [size]="13"></lucide-icon>
                      <span>{{ calendarService.isLoading() ? 'Đang xử lý...' : 'Ngắt kết nối' }}</span>
                    </button>
                  </div>
                }
              </section>

              <!-- WebCal Calendar Feed Card -->
              <section class="bg-white rounded-2xl border border-[#EAE8E7] p-6 sm:p-8 shadow-xs space-y-4">
                <div class="border-b border-[#EAE8E7] pb-4">
                  <span class="text-[11px] font-mono uppercase tracking-widest text-[#246B4A] font-semibold">
                    Đồng Bộ Qua URL (iCalendar / WebCal)
                  </span>
                  <h2 class="text-xl sm:text-2xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                    Liên Kết Nguồn Cấp Lịch (WebCal Feed)
                  </h2>
                  <p class="text-xs sm:text-sm text-[#656464] mt-1">
                    Dành cho Apple Calendar, Microsoft Outlook hoặc các ứng dụng hỗ trợ chuẩn URL .ics.
                  </p>
                </div>

                <div class="space-y-3">
                  <div class="flex flex-col sm:flex-row sm:items-center gap-2">
                    <input
                      type="text"
                      [value]="webcalUrl()"
                      readonly
                      aria-label="Địa chỉ nguồn cấp lịch WebCal"
                      data-testid="webcal-url-input"
                      class="w-full px-3.5 py-2.5 rounded-xl border border-[#EAE8E7] bg-[#FBF9F8] text-xs font-mono text-[#1B1C1C] focus:outline-none"
                    />
                    <div class="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        (click)="onCopyWebcalUrl()"
                        class="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-semibold bg-[#246B4A] text-white hover:bg-[#1B5338] transition-colors shadow-2xs cursor-pointer"
                      >
                        <lucide-icon name="copy" [size]="13"></lucide-icon>
                        <span>Sao chép</span>
                      </button>
                      <button
                        type="button"
                        (click)="onResetWebcalToken()"
                        class="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold border border-[#EAE8E7] bg-white text-[#656464] hover:text-[#1B1C1C] hover:bg-neutral-100 transition-colors shadow-2xs cursor-pointer"
                        title="Tạo lại mã token mới nếu bị lộ"
                      >
                        <lucide-icon name="rotate-ccw" [size]="13"></lucide-icon>
                        <span>Tạo token mới</span>
                      </button>
                    </div>
                  </div>
                  <p class="text-[11px] text-[#656464]">
                    Chỉ chia sẻ liên kết này với thiết bị cá nhân của bạn để đảm bảo bảo mật lịch trình học.
                  </p>
                </div>
              </section>

            </div>
          }

          <!-- ================= TAB 4: TÀI KHOẢN & BẢO MẬT ================= -->
          @if (activeTab() === 'security') {
            <div role="tabpanel" id="panel-security" aria-labelledby="tab-security" class="space-y-6">

              <!-- Change Password Form Card (Argon2id) -->
              <section class="bg-white rounded-2xl border border-[#EAE8E7] p-6 sm:p-8 shadow-xs space-y-6">
                <div class="border-b border-[#EAE8E7] pb-4">
                  <span class="text-[11px] font-mono uppercase tracking-widest text-[#246B4A] font-semibold">
                    An Toàn Mật Khẩu
                  </span>
                  <h2 class="text-xl sm:text-2xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                    Đổi Mật Khẩu Tài Khoản
                  </h2>
                  <p class="text-xs sm:text-sm text-[#656464] mt-1">
                    Mật khẩu được băm và mã hóa an toàn bằng thuật toán Argon2id. Đổi mật khẩu sẽ tự động thu hồi tất cả các phiên đăng nhập khác.
                  </p>
                </div>

                <form [formGroup]="passwordForm" (ngSubmit)="onChangePassword()" class="space-y-4 max-w-xl">
                  <!-- Current Password -->
                  <div>
                    <label for="current_password" class="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] font-mono mb-1.5">
                      Mật khẩu hiện tại
                    </label>
                    <input
                      id="current_password"
                      type="password"
                      formControlName="current_password"
                      class="w-full px-3.5 py-2.5 rounded-xl border border-[#EAE8E7] bg-white text-sm text-[#1B1C1C] focus:outline-none focus:border-[#246B4A] focus:ring-1 focus:ring-[#246B4A] transition-colors"
                      placeholder="Nhập mật khẩu đang sử dụng..."
                    />
                    @if (passwordForm.get('current_password')?.invalid && passwordForm.get('current_password')?.touched) {
                      <p class="text-xs text-[#BA1A1A] mt-1">Vui lòng cung cấp mật khẩu hiện tại.</p>
                    }
                  </div>

                  <!-- New Password -->
                  <div>
                    <label for="new_password" class="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] font-mono mb-1.5">
                      Mật khẩu mới
                    </label>
                    <input
                      id="new_password"
                      type="password"
                      formControlName="new_password"
                      (input)="checkPasswordStrength()"
                      class="w-full px-3.5 py-2.5 rounded-xl border border-[#EAE8E7] bg-white text-sm text-[#1B1C1C] focus:outline-none focus:border-[#246B4A] focus:ring-1 focus:ring-[#246B4A] transition-colors"
                      placeholder="Nhập mật khẩu mới..."
                    />

                    <!-- Password Requirements Checklist -->
                    <div class="mt-2.5 p-3.5 rounded-xl bg-[#FBF9F8] border border-[#EAE8E7] space-y-1.5 text-xs font-mono">
                      <span class="text-[10px] text-[#656464] uppercase font-bold block mb-1">Tiêu chuẩn mật khẩu an toàn:</span>
                      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <div class="flex items-center gap-1.5" [class.text-[#246B4A]]="hasMinLength()" [class.text-[#656464]]="!hasMinLength()">
                          <lucide-icon [name]="hasMinLength() ? 'check' : 'alert-triangle'" [size]="12"></lucide-icon>
                          <span>Tối thiểu 8 ký tự</span>
                        </div>
                        <div class="flex items-center gap-1.5" [class.text-[#246B4A]]="hasUpper()" [class.text-[#656464]]="!hasUpper()">
                          <lucide-icon [name]="hasUpper() ? 'check' : 'alert-triangle'" [size]="12"></lucide-icon>
                          <span>Chứa chữ hoa (A-Z)</span>
                        </div>
                        <div class="flex items-center gap-1.5" [class.text-[#246B4A]]="hasLower()" [class.text-[#656464]]="!hasLower()">
                          <lucide-icon [name]="hasLower() ? 'check' : 'alert-triangle'" [size]="12"></lucide-icon>
                          <span>Chứa chữ thường (a-z)</span>
                        </div>
                        <div class="flex items-center gap-1.5" [class.text-[#246B4A]]="hasNumberOrSpecial()" [class.text-[#656464]]="!hasNumberOrSpecial()">
                          <lucide-icon [name]="hasNumberOrSpecial() ? 'check' : 'alert-triangle'" [size]="12"></lucide-icon>
                          <span>Chứa số hoặc ký tự đặc biệt</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Confirm New Password -->
                  <div>
                    <label for="confirm_password" class="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] font-mono mb-1.5">
                      Xác nhận mật khẩu mới
                    </label>
                    <input
                      id="confirm_password"
                      type="password"
                      formControlName="confirm_password"
                      class="w-full px-3.5 py-2.5 rounded-xl border border-[#EAE8E7] bg-white text-sm text-[#1B1C1C] focus:outline-none focus:border-[#246B4A] focus:ring-1 focus:ring-[#246B4A] transition-colors"
                      placeholder="Nhập lại mật khẩu mới..."
                    />
                    @if (passwordsMismatch()) {
                      <p class="text-xs text-[#BA1A1A] mt-1 flex items-center gap-1">
                        <lucide-icon name="alert-triangle" [size]="12"></lucide-icon>
                        <span>Mật khẩu xác nhận không khớp.</span>
                      </p>
                    }
                  </div>

                  <!-- Action Button -->
                  <div class="pt-3">
                    <button
                      type="submit"
                      [disabled]="passwordForm.invalid || passwordsMismatch() || !isPasswordStrong() || settingsService.passwordSaving()"
                      class="inline-flex items-center gap-2 px-6 py-2.5 rounded-full text-xs font-semibold text-white bg-[#246B4A] hover:bg-[#1B5338] transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-2xs cursor-pointer"
                    >
                      @if (settingsService.passwordSaving()) {
                        <div class="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        <span>Đang cập nhật...</span>
                      } @else {
                        <lucide-icon name="lock" [size]="13"></lucide-icon>
                        <span>Cập nhật mật khẩu mới</span>
                      }
                    </button>
                  </div>
                </form>
              </section>

              <!-- GDPR Data Export Card -->
              <section class="bg-white rounded-2xl border border-[#EAE8E7] p-6 sm:p-8 shadow-xs space-y-4">
                <div class="border-b border-[#EAE8E7] pb-4">
                  <span class="text-[11px] font-mono uppercase tracking-widest text-[#246B4A] font-semibold">
                    Quyền Chuyển Đổi Dữ Liệu
                  </span>
                  <h2 class="text-xl sm:text-2xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                    Xuất Dữ Liệu Cá Nhân (GDPR Điều 20)
                  </h2>
                  <p class="text-xs sm:text-sm text-[#656464] mt-1">
                    Tải về toàn bộ hồ sơ người học, lịch sử phiên tập trung Pomodoro và cấu hình thời gian rảnh dưới định dạng tệp JSON mở.
                  </p>
                </div>

                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl border border-[#EAE8E7] bg-[#FBF9F8]">
                  <div class="space-y-0.5">
                    <div class="text-xs font-semibold text-[#1B1C1C]">Gói dữ liệu hoàn chỉnh (JSON format)</div>
                    <p class="text-[11px] text-[#656464]">Bao gồm thông tin hồ sơ, thống kê chu kỳ và cài đặt tùy chọn.</p>
                  </div>
                  <button
                    type="button"
                    (click)="onExportData()"
                    class="inline-flex items-center gap-2 px-4 py-2.5 rounded-full text-xs font-semibold bg-white border border-[#EAE8E7] text-[#1B1C1C] hover:border-[#246B4A] hover:text-[#246B4A] transition-colors shadow-2xs cursor-pointer self-start sm:self-auto shrink-0"
                  >
                    <lucide-icon name="download" [size]="13"></lucide-icon>
                    <span>Tải xuống dữ liệu (JSON)</span>
                  </button>
                </div>
              </section>

              <!-- Account Deletion Danger Zone -->
              <section class="bg-white rounded-2xl border border-rose-200 p-6 sm:p-8 shadow-xs space-y-6">
                <div class="border-b border-rose-100 pb-4">
                  <span class="text-[11px] font-mono uppercase tracking-widest text-[#BA1A1A] font-semibold">
                    Khu Vực Nguy Hiểm
                  </span>
                  <h2 class="text-xl sm:text-2xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                    Đóng & Xóa Vĩnh Viễn Tài Khoản (GDPR Điều 17)
                  </h2>
                  <p class="text-xs sm:text-sm text-[#656464] mt-1">
                    Thực thi quyền được lãng quên. Toàn bộ thông tin định danh (PII), tiến trình học tập và liên kết WebCal sẽ bị hủy vĩnh viễn.
                  </p>
                </div>

                <div class="rounded-xl border border-rose-200 bg-rose-50/60 p-4 text-xs text-rose-900 space-y-1">
                  <div class="flex items-center gap-2 font-semibold">
                    <lucide-icon name="alert-triangle" [size]="14" class="text-rose-700"></lucide-icon>
                    <span>Cảnh báo hành động không thể hoàn tác:</span>
                  </div>
                  <p class="leading-relaxed">
                    Khi tài khoản bị xóa, toàn bộ dữ liệu lộ trình học, số liệu Pomodoro và lịch rảnh sẽ bị xóa vĩnh viễn khỏi máy chủ.
                  </p>
                </div>

                <div class="flex justify-end pt-2">
                  <button
                    type="button"
                    (click)="onRequestDeleteAccount()"
                    class="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-semibold text-white bg-[#BA1A1A] hover:bg-rose-700 transition-colors shadow-2xs cursor-pointer"
                  >
                    <lucide-icon name="trash-2" [size]="13"></lucide-icon>
                    <span>Yêu cầu xóa tài khoản vĩnh viễn</span>
                  </button>
                </div>
              </section>

            </div>
          }

        </main>

      </div>
    </div>
  `,
})
export class SettingsPageComponent implements OnInit, OnDestroy {
  readonly settingsService = inject(SettingsService);
  readonly calendarService = inject(CalendarIntegrationService);
  private readonly authService = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly messageService = inject(MessageService, { optional: true });
  private readonly confirmationService = inject(ConfirmationService, { optional: true });

  readonly preferences = this.settingsService.preferences;
  readonly quota = this.settingsService.quota;
  readonly defaultCycleEnd = new Date(Date.now() + 30 * 86400000).toISOString();

  readonly activeTab = signal<SettingsTab>('general');
  private queryParamsSub?: Subscription;

  readonly webcalUrl = signal<string>(
    'webcal://focusflow.app/api/v1/calendar/feed.ics?token=ff_live_sec_789123'
  );

  readonly userTier = computed<string>(() => {
    return (this.authService.currentUser()?.tier || 'FREE').toUpperCase();
  });

  readonly quotaUsagePercent = computed<number>(() => {
    const q = this.quota();
    if (q && q.monthly_limit > 0) {
      return Math.max(0, Math.min(100, (q.used_calls / q.monthly_limit) * 100));
    }
    const prefs = this.preferences();
    const limit = prefs.aiCreditsLimit || 10;
    const used = prefs.aiCreditsUsed || 0;
    return Math.max(0, Math.min(100, (used / limit) * 100));
  });

  // Password Strength Indicators
  readonly hasMinLength = signal(false);
  readonly hasUpper = signal(false);
  readonly hasLower = signal(false);
  readonly hasNumberOrSpecial = signal(false);
  private passwordSub?: Subscription;

  passwordForm: FormGroup = this.fb.group({
    current_password: ['', [Validators.required]],
    new_password: ['', [Validators.required, Validators.minLength(8)]],
    confirm_password: ['', [Validators.required]],
  });

  ngOnInit(): void {
    this.calendarService.checkUrlCallback(this.route, this.router);
    this.calendarService.loadStatus().subscribe();
    void this.settingsService.loadQuota();

    const initialTab = this.route.snapshot.queryParamMap.get('tab') as SettingsTab | null;
    if (initialTab && this.isValidTab(initialTab)) {
      this.activeTab.set(initialTab);
    }

    this.queryParamsSub = this.route.queryParamMap.subscribe((params) => {
      if (params.has('calendar_connected')) {
        this.activeTab.set('calendar');
        return;
      }
      const tab = params.get('tab') as SettingsTab | null;
      const targetTab: SettingsTab = tab && this.isValidTab(tab) ? tab : 'general';
      if (targetTab !== this.activeTab()) {
        this.activeTab.set(targetTab);
      }
    });

    this.passwordSub = this.passwordForm.get('new_password')?.valueChanges.subscribe(() => {
      this.checkPasswordStrength();
    });
  }

  ngOnDestroy(): void {
    this.queryParamsSub?.unsubscribe();
    this.passwordSub?.unsubscribe();
  }

  private isValidTab(tab: string): tab is SettingsTab {
    return ['general', 'ai', 'calendar', 'security'].includes(tab);
  }

  setTab(tab: SettingsTab): void {
    this.activeTab.set(tab);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { tab },
      queryParamsHandling: 'merge',
    });
  }

  onTabKeydown(event: KeyboardEvent, currentTab: SettingsTab): void {
    const tabs: SettingsTab[] = ['general', 'ai', 'calendar', 'security'];
    const idx = tabs.indexOf(currentTab);
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      event.preventDefault();
      const nextTab = tabs[(idx + 1) % tabs.length];
      this.setTab(nextTab);
      document.getElementById(`tab-${nextTab}`)?.focus();
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      event.preventDefault();
      const prevTab = tabs[(idx - 1 + tabs.length) % tabs.length];
      this.setTab(prevTab);
      document.getElementById(`tab-${prevTab}`)?.focus();
    }
  }

  onConnectGoogleCalendar(): void {
    this.calendarService.connectGoogleCalendar('/settings?tab=calendar');
  }

  onDisconnectGoogleCalendar(): void {
    if (this.confirmationService) {
      this.confirmationService.confirm({
        message:
          'Bạn có chắc chắn muốn ngắt kết nối Google Calendar? Các sự kiện học tập tương lai sẽ không còn được tự động đồng bộ.',
        header: 'Xác nhận ngắt kết nối',
        icon: 'pi pi-exclamation-triangle',
        acceptLabel: 'Ngắt kết nối',
        rejectLabel: 'Giữ liên kết',
        acceptButtonStyleClass: 'p-button-danger',
        accept: () => {
          this.calendarService.disconnectGoogleCalendar().subscribe();
        },
      });
    } else {
      if (confirm('Bạn có chắc chắn muốn ngắt kết nối Google Calendar?')) {
        this.calendarService.disconnectGoogleCalendar().subscribe();
      }
    }
  }

  scrollToSection(event: Event, sectionId: string): void {
    event.preventDefault();
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  updatePreference<K extends keyof ReturnType<typeof this.preferences>>(
    key: K,
    val: ReturnType<typeof this.preferences>[K]
  ): void {
    this.settingsService.savePreferences({ [key]: val });
    this.messageService?.add({
      severity: 'success',
      summary: 'Đã lưu tùy chọn',
      detail: 'Tùy chọn học tập đã được cập nhật thành công.',
      life: 2500,
    });
  }

  reloadQuota(): void {
    void this.settingsService.loadQuota();
  }

  onUpgradePlan(): void {
    this.messageService?.add({
      severity: 'info',
      summary: 'Gói dịch vụ',
      detail: 'Tính năng cổng thanh toán PRO đang được kết nối trong phiên bản tiếp theo.',
      life: 4000,
    });
  }

  async onCopyWebcalUrl(): Promise<void> {
    try {
      await navigator.clipboard.writeText(this.webcalUrl());
      this.messageService?.add({
        severity: 'success',
        summary: 'Đã sao chép liên kết',
        detail: 'Địa chỉ WebCal feed đã được lưu vào bộ nhớ tạm.',
        life: 3000,
      });
    } catch {
      this.messageService?.add({
        severity: 'warn',
        summary: 'Sao chép thủ công',
        detail: 'Hãy chọn và sao chép trực tiếp từ ô nhập liệu.',
        life: 4000,
      });
    }
  }

  onResetWebcalToken(): void {
    if (this.confirmationService) {
      this.confirmationService.confirm({
        message: 'Đặt lại token sẽ vô hiệu hóa tất cả các ứng dụng lịch đang đồng bộ. Bạn có chắc chắn muốn tiếp tục?',
        header: 'Đặt lại WebCal Token',
        icon: 'pi pi-refresh',
        acceptLabel: 'Xác nhận tạo mới',
        rejectLabel: 'Hủy',
        accept: () => {
          void this.executeResetWebcal();
        },
      });
    } else {
      if (confirm('Đặt lại token sẽ vô hiệu hóa tất cả các ứng dụng lịch đang đồng bộ. Tiếp tục?')) {
        void this.executeResetWebcal();
      }
    }
  }

  private async executeResetWebcal(): Promise<void> {
    const res = await this.settingsService.resetWebCalToken();
    this.webcalUrl.set(res.webcal_url);
    this.messageService?.add({
      severity: 'success',
      summary: 'Đã tạo token mới',
      detail: 'Địa chỉ WebCal mới đã sẵn sàng. Hãy cập nhật vào ứng dụng lịch của bạn.',
      life: 4000,
    });
  }

  onExportData(): void {
    const data = {
      user: this.authService.currentUser(),
      preferences: this.preferences(),
      quota: this.quota(),
      exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `focusflow-learner-data-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    this.messageService?.add({
      severity: 'success',
      summary: 'Đã xuất dữ liệu',
      detail: 'Tệp JSON chứa toàn bộ dữ liệu học tập cá nhân đã được tải về.',
      life: 4000,
    });
  }

  checkPasswordStrength(): void {
    const pwd = this.passwordForm.get('new_password')?.value || '';
    this.hasMinLength.set(pwd.length >= 8);
    this.hasUpper.set(/[A-Z]/.test(pwd));
    this.hasLower.set(/[a-z]/.test(pwd));
    this.hasNumberOrSpecial.set(/[0-9!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(pwd));
  }

  isPasswordStrong(): boolean {
    return (
      this.hasMinLength() &&
      this.hasUpper() &&
      this.hasLower() &&
      this.hasNumberOrSpecial()
    );
  }

  passwordsMismatch(): boolean {
    const newPwd = this.passwordForm.get('new_password')?.value;
    const confirmPwd = this.passwordForm.get('confirm_password')?.value;
    if (!confirmPwd) return false;
    return newPwd !== confirmPwd;
  }

  async onChangePassword(): Promise<void> {
    if (this.passwordForm.invalid || this.passwordsMismatch() || !this.isPasswordStrong()) {
      return;
    }

    const { current_password, new_password } = this.passwordForm.value;
    try {
      await this.settingsService.changePassword({
        current_password,
        new_password,
      });
      this.passwordForm.reset();
      this.hasMinLength.set(false);
      this.hasUpper.set(false);
      this.hasLower.set(false);
      this.hasNumberOrSpecial.set(false);

      this.messageService?.add({
        severity: 'success',
        summary: 'Đổi mật khẩu thành công',
        detail: 'Mật khẩu đã được cập nhật. Mọi phiên đăng nhập cũ đã được thu hồi.',
        life: 5000,
      });
    } catch {
      this.messageService?.add({
        severity: 'error',
        summary: 'Lỗi đổi mật khẩu',
        detail: 'Mật khẩu hiện tại không chính xác hoặc không đáp ứng tiêu chuẩn an toàn.',
        life: 5000,
      });
    }
  }

  onRequestDeleteAccount(): void {
    if (this.confirmationService) {
      this.confirmationService.confirm({
        message: 'Hành động này là vĩnh viễn và không thể khôi phục theo GDPR Điều 17. Bạn có tuyệt đối chắc chắn muốn xóa tài khoản?',
        header: 'Xác nhận Xóa Vĩnh Viễn Tài Khoản',
        icon: 'pi pi-trash',
        acceptLabel: 'Xóa tài khoản vĩnh viễn',
        rejectLabel: 'Hủy bỏ',
        acceptButtonStyleClass: 'p-button-danger',
        accept: () => {
          this.messageService?.add({
            severity: 'warn',
            summary: 'Đang gửi yêu cầu',
            detail: 'Yêu cầu xóa tài khoản đã được chuyển đến bộ phận bảo mật GDPR.',
            life: 5000,
          });
        },
      });
    } else {
      if (confirm('Bạn có chắc chắn muốn xóa vĩnh viễn tài khoản của mình?')) {
        this.messageService?.add({
          severity: 'warn',
          summary: 'Đang gửi yêu cầu',
          detail: 'Yêu cầu xóa tài khoản đã được chuyển đến bộ phận bảo mật GDPR.',
          life: 5000,
        });
      }
    }
  }
}
