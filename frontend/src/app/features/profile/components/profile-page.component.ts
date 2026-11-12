import {
  Component,
  ChangeDetectionStrategy,
  inject,
  signal,
  computed,
  OnInit,
} from '@angular/core';
import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import {
  LucideAngularModule,
  LUCIDE_ICONS,
  LucideIconProvider,
  User,
  Check,
  Lock,
  Shield,
  RotateCcw,
  Sparkles,
  Clock,
  Brain,
  Compass,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Layers,
  ArrowRight,
} from 'lucide-angular';
import { ConfirmationService, MessageService } from 'primeng/api';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ToastModule } from 'primeng/toast';
import { ProfileService } from '../services/profile.service';
import type { LearnerMemoryResponseDTO } from '../models/profile.model';

interface TimezoneOption {
  value: string;
  label: string;
  offset: string;
}

@Component({
  selector: 'app-profile-page',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
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
        User,
        Check,
        Lock,
        Shield,
        RotateCcw,
        Sparkles,
        Clock,
        Brain,
        Compass,
        Filter,
        CheckCircle2,
        XCircle,
        AlertTriangle,
        Layers,
        ArrowRight,
      }),
    },
  ],
  template: `
    <div class="min-h-screen bg-[#FBF9F8] text-[#1B1C1C] py-8 px-4 sm:px-6 lg:px-8">
      <div class="max-w-7xl mx-auto space-y-8">
        <!-- Top Editorial Header -->
        <header class="border-b border-[#EAE8E7] pb-6">
          <div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <span class="text-[11px] font-semibold tracking-widest uppercase text-[#246B4A] font-mono">
                Hệ Thống Nhận Thức & Danh Tính Cá Nhân
              </span>
              <h1 class="text-3xl sm:text-4xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                Hồ Sơ Người Học
              </h1>
              <p class="text-sm text-[#656464] mt-1.5 max-w-2xl font-sans">
                Định danh tài khoản, quy chuẩn múi giờ IANA và hệ thống nhận thức Zimmerman SRL giúp mô hình AI thấu hiểu phong cách học tập của bạn.
              </p>
            </div>
            <div class="flex items-center gap-2 text-xs font-mono text-[#656464] bg-white border border-[#EAE8E7] px-3 py-1.5 rounded-full shadow-2xs self-start md:self-auto">
              <span class="w-2 h-2 rounded-full bg-[#246B4A] animate-pulse"></span>
              <span>SRL State: Adaptive Active</span>
            </div>
          </div>
        </header>

        <!-- 2-Column Master-Detail Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <!-- Left Column (lg:col-span-4): Identity Card & Sticky Index -->
          <aside class="lg:col-span-4 space-y-6 lg:sticky lg:top-24">
            <!-- Identity Hero Card -->
            <div class="bg-white rounded-xl border border-[#EAE8E7] p-6 shadow-2xs space-y-6">
              <div class="flex flex-col items-center text-center">
                <!-- Monogram Avatar -->
                <div class="w-[72px] h-[72px] rounded-full bg-[#246B4A]/10 text-[#246B4A] border border-[#246B4A]/25 font-bold text-2xl flex items-center justify-center font-serif shadow-2xs">
                  {{ userInitials() }}
                </div>

                <!-- Full Name & Badges -->
                <h2 class="text-xl font-bold font-serif text-[#1B1C1C] tracking-tight mt-3">
                  {{ profile()?.full_name || 'Đang tải...' }}
                </h2>

                <!-- Email with verified check -->
                <div class="flex items-center gap-1.5 text-xs text-[#656464] mt-1 font-mono">
                  <span>{{ profile()?.email || '' }}</span>
                  <span class="inline-flex items-center text-[#246B4A]" title="Email đã xác thực">
                    <lucide-icon name="check-circle-2" [size]="13" class="shrink-0"></lucide-icon>
                  </span>
                </div>

                <!-- Tier & Role Pills -->
                <div class="flex items-center gap-2 mt-3">
                  <span
                    class="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold tracking-wide uppercase border"
                    [ngClass]="{
                      'bg-emerald-50 text-[#246B4A] border-emerald-200': profile()?.tier === 'PRO' || profile()?.tier === 'PREMIUM',
                      'bg-neutral-100 text-[#555555] border-neutral-200': profile()?.tier !== 'PRO' && profile()?.tier !== 'PREMIUM'
                    }"
                  >
                    Gói {{ profile()?.tier || 'FREE' }}
                  </span>
                  <span class="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium tracking-wide uppercase bg-neutral-50 text-[#656464] border border-[#EAE8E7]">
                    Vai trò: {{ profile()?.role || 'user' }}
                  </span>
                </div>
              </div>

              <!-- Metadata Divider -->
              <div class="border-t border-[#EAE8E7] pt-4 space-y-2.5 text-xs">
                <div class="flex justify-between items-center text-[#656464]">
                  <span>Múi giờ quy chuẩn:</span>
                  <span class="font-mono text-[#1B1C1C] font-medium">{{ profile()?.timezone || 'Asia/Ho_Chi_Minh' }}</span>
                </div>
                <div class="flex justify-between items-center text-[#656464]">
                  <span>Ngày khởi tạo:</span>
                  <span class="font-mono text-[#1B1C1C]">{{ profile()?.created_at | date: 'dd/MM/yyyy' }}</span>
                </div>
              </div>
            </div>

            <!-- Sticky Section Navigation Index -->
            <nav class="bg-white rounded-xl border border-[#EAE8E7] p-5 shadow-2xs space-y-2" aria-label="Chỉ mục hồ sơ">
              <span class="text-[11px] font-mono uppercase tracking-widest text-[#656464] font-semibold block mb-3">
                Chỉ mục điều hướng
              </span>
              <ul class="space-y-1 text-sm font-medium">
                <li>
                  <a
                    href="#personal-info"
                    (click)="scrollToSection($event, 'personal-info')"
                    class="flex items-center gap-2 px-3 py-2 rounded-lg text-[#1B1C1C] hover:bg-[#FBF9F8] hover:text-[#246B4A] transition-colors"
                  >
                    <span class="font-mono text-xs text-[#246B4A]">01</span>
                    <span>Thông tin cá nhân & Múi giờ</span>
                  </a>
                </li>
                <li>
                  <a
                    href="#srl-insights"
                    (click)="scrollToSection($event, 'srl-insights')"
                    class="flex items-center gap-2 px-3 py-2 rounded-lg text-[#1B1C1C] hover:bg-[#FBF9F8] hover:text-[#246B4A] transition-colors"
                  >
                    <span class="font-mono text-xs text-[#246B4A]">02</span>
                    <span>Thói quen học tập Zimmerman SRL</span>
                  </a>
                </li>
                <li>
                  <a
                    href="#learner-memory"
                    (click)="scrollToSection($event, 'learner-memory')"
                    class="flex items-center gap-2 px-3 py-2 rounded-lg text-[#1B1C1C] hover:bg-[#FBF9F8] hover:text-[#246B4A] transition-colors"
                  >
                    <span class="font-mono text-xs text-[#246B4A]">03</span>
                    <span>Bộ nhớ Learner Memory (4×3)</span>
                  </a>
                </li>
                <li>
                  <a
                    href="#danger-reset"
                    (click)="scrollToSection($event, 'danger-reset')"
                    class="flex items-center gap-2 px-3 py-2 rounded-lg text-[#BA1A1A] hover:bg-rose-50 transition-colors"
                  >
                    <span class="font-mono text-xs text-[#BA1A1A]">04</span>
                    <span>Đặt lại Cold Start</span>
                  </a>
                </li>
              </ul>
            </nav>
          </aside>

          <!-- Right Column (lg:col-span-8): Content Sections -->
          <main class="lg:col-span-8 space-y-8">
            <!-- Section 1: Thông tin cá nhân & Múi giờ -->
            <section id="personal-info" class="bg-white rounded-xl border border-[#EAE8E7] p-6 sm:p-8 shadow-2xs space-y-6 scroll-mt-24">
              <div class="border-b border-[#EAE8E7] pb-4">
                <span class="text-[11px] font-mono uppercase tracking-widest text-[#246B4A] font-semibold">
                  Mục 01 / Cấu hình danh tính
                </span>
                <h3 class="text-xl sm:text-2xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                  Thông tin cơ bản & Quy chuẩn thời gian
                </h3>
                <p class="text-xs sm:text-sm text-[#656464] mt-1">
                  Múi giờ IANA được dùng làm mốc quy chiếu tính toán khung giờ học tập và quét nhiệm vụ quá hạn (FR-AUTH-003).
                </p>
              </div>

              <form [formGroup]="profileForm" (ngSubmit)="onSaveProfile()" class="space-y-5">
                <!-- Full Name Field -->
                <div>
                  <label for="full_name" class="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] font-mono mb-1.5">
                    Họ và tên người học
                  </label>
                  <input
                    id="full_name"
                    type="text"
                    formControlName="full_name"
                    class="w-full px-3.5 py-2.5 rounded-lg border border-[#EAE8E7] bg-white text-sm text-[#1B1C1C] focus:outline-none focus:border-[#111111] transition-colors"
                    placeholder="Nhập họ và tên đầy đủ..."
                  />
                  @if (profileForm.get('full_name')?.invalid && profileForm.get('full_name')?.touched) {
                    <p class="text-xs text-[#BA1A1A] mt-1.5 flex items-center gap-1">
                      <lucide-icon name="alert-triangle" [size]="12"></lucide-icon>
                      <span>Họ và tên phải có độ dài từ 2 đến 100 ký tự.</span>
                    </p>
                  }
                </div>

                <!-- Timezone Field -->
                <div>
                  <label for="timezone" class="block text-xs font-semibold uppercase tracking-wider text-[#1B1C1C] font-mono mb-1.5">
                    Múi giờ IANA (Chuẩn quốc tế)
                  </label>
                  <div class="relative">
                    <select
                      id="timezone"
                      formControlName="timezone"
                      class="w-full appearance-none px-3.5 py-2.5 pr-10 rounded-lg border border-[#EAE8E7] bg-white text-sm text-[#1B1C1C] font-mono focus:outline-none focus:border-[#111111] transition-colors"
                    >
                      @for (tz of timezoneOptions; track tz.value) {
                        <option [value]="tz.value">
                          {{ tz.label }} ({{ tz.offset }})
                        </option>
                      }
                    </select>
                    <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-[#656464]">
                      <lucide-icon name="clock" [size]="14"></lucide-icon>
                    </div>
                  </div>
                  <p class="text-[11px] text-[#656464] mt-1.5">
                    Tất cả các cảnh báo quá hạn và slot học trong tuần được căn chỉnh chính xác theo múi giờ này.
                  </p>
                </div>

                <!-- Readonly Email Field -->
                <div>
                  <label class="block text-xs font-semibold uppercase tracking-wider text-[#656464] font-mono mb-1.5">
                    Địa chỉ Email (Định danh đăng nhập)
                  </label>
                  <div class="relative">
                    <input
                      type="email"
                      [value]="profile()?.email || ''"
                      readonly
                      class="w-full px-3.5 py-2.5 pl-9 rounded-lg border border-[#EAE8E7] bg-[#F5F3F3] text-sm text-[#656464] font-mono cursor-not-allowed select-all"
                    />
                    <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-[#656464]">
                      <lucide-icon name="lock" [size]="13"></lucide-icon>
                    </div>
                  </div>
                  <span class="text-[11px] text-[#656464] mt-1 block">
                    Không thể thay đổi vì lý do an toàn phiên làm việc và xác thực JWT.
                  </span>
                </div>

                <!-- Action Bar -->
                <div class="pt-3 flex items-center justify-end gap-3 border-t border-[#EAE8E7]">
                  <button
                    type="submit"
                    [disabled]="profileForm.invalid || profileForm.pristine || profileService.profileSaving()"
                    class="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-semibold text-white bg-[#246B4A] hover:bg-[#1B5338] transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-2xs"
                  >
                    @if (profileService.profileSaving()) {
                      <div class="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                      <span>Đang lưu thay đổi...</span>
                    } @else {
                      <lucide-icon name="check" [size]="13"></lucide-icon>
                      <span>Lưu thay đổi hồ sơ</span>
                    }
                  </button>
                </div>
              </form>
            </section>

            <!-- Section 2: Nhận thức Người học Zimmerman SRL -->
            <section id="srl-insights" class="bg-white rounded-xl border border-[#EAE8E7] p-6 sm:p-8 shadow-2xs space-y-6 scroll-mt-24">
              <div class="border-b border-[#EAE8E7] pb-4">
                <span class="text-[11px] font-mono uppercase tracking-widest text-[#246B4A] font-semibold">
                  Mục 02 / Mô hình học tập tự điều chỉnh
                </span>
                <h3 class="text-xl sm:text-2xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                  Hồ sơ Thói quen Học tập Zimmerman SRL
                </h3>
                <p class="text-xs sm:text-sm text-[#656464] mt-1">
                  Các chỉ số thực chứng theo mô hình 3 pha Zimmerman được tổng hợp qua lịch sử phiên Pomodoro (FR-PROFILE-001).
                </p>
              </div>

              <!-- 3 Metrics Grid -->
              <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <!-- Metric 1: Thời lượng học tối ưu -->
                <div class="bg-[#FBF9F8] rounded-xl border border-[#EAE8E7] p-4 space-y-2">
                  <div class="flex items-center justify-between text-[#656464]">
                    <span class="text-[11px] font-mono font-semibold uppercase tracking-wider">Thời lượng tối ưu</span>
                    <lucide-icon name="clock" [size]="14" class="text-[#246B4A]"></lucide-icon>
                  </div>
                  <div class="text-2xl font-bold font-serif text-[#1B1C1C]">
                    {{ srlMetrics().optSessionMinutes }} <span class="text-sm font-sans font-normal text-[#656464]">phút / phiên</span>
                  </div>
                  <p class="text-[11px] text-[#656464] leading-relaxed">
                    Khung thời gian tập trung cao độ đạt hiệu quả hấp thụ kiến thức tốt nhất.
                  </p>
                </div>

                <!-- Metric 2: Thiên kiến hoàn thành kế hoạch -->
                <div class="bg-[#FBF9F8] rounded-xl border border-[#EAE8E7] p-4 space-y-2">
                  <div class="flex items-center justify-between text-[#656464]">
                    <span class="text-[11px] font-mono font-semibold uppercase tracking-wider">Thiên kiến hoàn thành</span>
                    <lucide-icon name="compass" [size]="14" class="text-[#246B4A]"></lucide-icon>
                  </div>
                  <div class="text-2xl font-bold font-serif text-[#1B1C1C]">
                    {{ srlMetrics().completionRateBias | number: '1.2-2' }}x
                  </div>
                  <p class="text-[11px] text-[#656464] leading-relaxed">
                    Hệ số hiệu chỉnh tốc độ thực tế so với dự toán ban đầu của kế hoạch.
                  </p>
                </div>

                <!-- Metric 3: Phong cách học chủ đạo -->
                <div class="bg-[#FBF9F8] rounded-xl border border-[#EAE8E7] p-4 space-y-2">
                  <div class="flex items-center justify-between text-[#656464]">
                    <span class="text-[11px] font-mono font-semibold uppercase tracking-wider">Phong cách học</span>
                    <lucide-icon name="brain" [size]="14" class="text-[#246B4A]"></lucide-icon>
                  </div>
                  <div class="text-base font-bold font-serif text-[#1B1C1C] leading-snug">
                    Sequential Deep Work
                  </div>
                  <p class="text-[11px] text-[#656464] leading-relaxed">
                    Ưu tiên hoàn thành tuần tự từng khối kiến thức trước khi mở rộng.
                  </p>
                </div>
              </div>

              <div class="p-4 rounded-xl bg-emerald-50/60 border border-emerald-200/70 text-xs text-neutral-700 space-y-1">
                <span class="font-semibold text-[#246B4A] block">Ghi chú về vòng lặp SRL 3 Pha:</span>
                <p class="text-[11px] leading-relaxed text-neutral-600">
                  Chu trình <strong>Forethought (Đặt mục tiêu)</strong> &rarr; <strong>Performance (Tập trung với Pomodoro)</strong> &rarr; <strong>Self-Reflection (Đánh giá sau phiên)</strong> được tự động tích lũy và cập nhật liên tục vào hồ sơ học viên.
                </p>
              </div>
            </section>

            <!-- Section 3: Bộ nhớ Cấu trúc hóa 4×3 -->
            <section id="learner-memory" class="bg-white rounded-xl border border-[#EAE8E7] p-6 sm:p-8 shadow-2xs space-y-6 scroll-mt-24">
              <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[#EAE8E7] pb-4">
                <div>
                  <span class="text-[11px] font-mono uppercase tracking-widest text-[#246B4A] font-semibold">
                    Mục 03 / Bộ nhớ nhận thức 4×3
                  </span>
                  <h3 class="text-xl sm:text-2xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                    Bộ nhớ Học tập Cấu trúc hóa (Learner Memory)
                  </h3>
                  <p class="text-xs sm:text-sm text-[#656464] mt-1">
                    Duy trì độc lập xuyên suốt nhiều Roadmap. Bạn có toàn quyền xác nhận hoặc từ chối các suy luận tự động của AI.
                  </p>
                </div>

                <button
                  type="button"
                  (click)="reloadMemory()"
                  class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-mono border border-[#EAE8E7] bg-[#FBF9F8] hover:bg-neutral-100 transition-colors self-start sm:self-auto cursor-pointer"
                  title="Tải lại danh sách"
                >
                  <lucide-icon name="rotate-ccw" [size]="12"></lucide-icon>
                  <span>Làm mới</span>
                </button>
              </div>

              <!-- Category Filter Pills -->
              <div class="flex flex-wrap items-center gap-1.5">
                @for (cat of memoryCategories; track cat.id) {
                  <button
                    type="button"
                    (click)="selectedCategory.set(cat.id)"
                    class="px-3 py-1 rounded-full text-xs font-mono transition-colors border cursor-pointer"
                    [ngClass]="{
                      'bg-[#246B4A] text-white border-[#246B4A] font-semibold': selectedCategory() === cat.id,
                      'bg-white text-[#656464] border-[#EAE8E7] hover:border-neutral-400': selectedCategory() !== cat.id
                    }"
                  >
                    {{ cat.label }}
                  </button>
                }
              </div>

              <!-- Memory List / Empty States -->
              @if (profileService.memoryLoading()) {
                <div class="py-12 flex flex-col items-center justify-center space-y-3 text-center">
                  <div class="w-6 h-6 border-2 border-neutral-300 border-t-[#246B4A] rounded-full animate-spin"></div>
                  <span class="text-xs text-[#656464] font-mono">Đang truy xuất Learner Memory...</span>
                </div>
              } @else if (profileService.memoryError(); as error) {
                <div class="p-4 rounded-xl border border-rose-200 bg-rose-50/70 text-xs text-rose-800 flex items-center justify-between">
                  <span>{{ error }}</span>
                  <button
                    type="button"
                    (click)="reloadMemory()"
                    class="font-semibold underline ml-3"
                  >
                    Thử lại
                  </button>
                </div>
              } @else if (filteredMemories().length === 0) {
                <div class="py-12 px-6 rounded-xl border border-dashed border-[#EAE8E7] bg-[#FBF9F8] text-center space-y-2">
                  <div class="w-10 h-10 rounded-full bg-neutral-200/60 mx-auto flex items-center justify-center text-[#656464]">
                    <lucide-icon name="layers" [size]="18"></lucide-icon>
                  </div>
                  <h4 class="text-sm font-semibold font-serif text-[#1B1C1C]">Chưa có bản ghi ký ức nào</h4>
                  <p class="text-xs text-[#656464] max-w-md mx-auto">
                    Hệ thống sẽ tự động tổng hợp thói quen và kỹ năng sau khi bạn hoàn thành các phiên học Pomodoro hoặc xác nhận trực tiếp.
                  </p>
                </div>
              } @else {
                <div class="space-y-3">
                  @for (item of filteredMemories(); track item.id) {
                    <article class="p-4 rounded-xl border border-[#EAE8E7] bg-[#FBF9F8] hover:bg-white transition-all space-y-3">
                      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div class="flex items-center gap-2 flex-wrap">
                          <span class="font-mono text-xs font-bold text-[#1B1C1C]">{{ item.memory_key }}</span>
                          <span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-neutral-200/80 text-neutral-800">
                            {{ item.category }}
                          </span>
                          <span
                            class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase border"
                            [ngClass]="{
                              'bg-emerald-50 text-[#246B4A] border-emerald-200': item.epistemic_level === 'EXPLICIT',
                              'bg-blue-50 text-blue-700 border-blue-200': item.epistemic_level === 'OBSERVED',
                              'bg-amber-50 text-amber-700 border-amber-200': item.epistemic_level === 'INFERRED'
                            }"
                          >
                            {{ item.epistemic_level }}
                          </span>
                        </div>

                        <!-- Confidence Bar -->
                        <div class="flex items-center gap-2 text-xs font-mono text-[#656464]">
                          <span>Độ tin cậy:</span>
                          <div class="w-16 h-1.5 rounded-full bg-neutral-200 overflow-hidden">
                            <div
                              class="h-full bg-[#246B4A]"
                              [style.width.%]="item.confidence * 100"
                            ></div>
                          </div>
                          <span class="font-bold text-[#1B1C1C]">{{ item.confidence * 100 | number: '1.0-0' }}%</span>
                        </div>
                      </div>

                      <!-- Raw Value Presentation -->
                      <div class="bg-white p-3 rounded-lg border border-[#EAE8E7] font-mono text-xs text-[#1B1C1C] overflow-x-auto">
                        <span class="text-[#656464] block text-[10px] uppercase font-semibold mb-1">Dữ liệu quan trắc:</span>
                        {{ formatValue(item.value) }}
                      </div>

                      <!-- Metadata & Actions -->
                      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1 text-xs">
                        <span class="text-[11px] text-[#656464] font-mono">
                          Mẫu quan sát: {{ item.sample_size }} lần
                        </span>

                        <div class="flex items-center gap-2">
                          <button
                            type="button"
                            (click)="onConfirmMemory(item.id)"
                            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border border-emerald-300 bg-emerald-50 text-[#246B4A] hover:bg-emerald-100 transition-colors cursor-pointer"
                          >
                            <lucide-icon name="check" [size]="12"></lucide-icon>
                            <span>Xác nhận</span>
                          </button>
                          <button
                            type="button"
                            (click)="onRejectMemory(item.id)"
                            class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border border-rose-200 bg-rose-50 text-rose-700 hover:bg-rose-100 transition-colors cursor-pointer"
                          >
                            <lucide-icon name="x-circle" [size]="12"></lucide-icon>
                            <span>Từ chối inference</span>
                          </button>
                        </div>
                      </div>
                    </article>
                  }
                </div>
              }
            </section>

            <!-- Section 4: Đặt lại Hồ sơ (Cold Start) -->
            <section id="danger-reset" class="bg-white rounded-xl border border-rose-200 p-6 sm:p-8 shadow-2xs space-y-6 scroll-mt-24">
              <div class="border-b border-rose-100 pb-4">
                <span class="text-[11px] font-mono uppercase tracking-widest text-[#BA1A1A] font-semibold">
                  Mục 04 / Quản trị dữ liệu nhận thức
                </span>
                <h3 class="text-xl sm:text-2xl font-serif font-bold text-[#1B1C1C] tracking-tight mt-1">
                  Đặt Lại Hồ Sơ (Cold Start)
                </h3>
                <p class="text-xs sm:text-sm text-[#656464] mt-1">
                  Đưa Learner Profile về trạng thái Cold Start (xóa toàn bộ memory & mastery, giữ nguyên lịch sử phiên học Pomodoro).
                </p>
              </div>

              <div class="rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-900 space-y-1">
                <div class="flex items-center gap-2 font-semibold">
                  <lucide-icon name="alert-triangle" [size]="14" class="text-amber-700"></lucide-icon>
                  <span>Lưu ý về cơ chế Cold Start:</span>
                </div>
                <p class="leading-relaxed">
                  Hành động này sẽ xóa sạch các mô hình thói quen đã huấn luyện. Trợ lý AI sẽ thu thập lại dữ liệu từ đầu như một học viên mới, nhưng dữ liệu Roadmap và Task của bạn hoàn toàn không bị ảnh hưởng.
                </p>
              </div>

              <div class="flex justify-end pt-2">
                <button
                  type="button"
                  (click)="onRequestReset()"
                  class="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-semibold text-rose-700 border border-rose-300 bg-rose-50 hover:bg-rose-100 transition-colors shadow-2xs cursor-pointer"
                >
                  <lucide-icon name="rotate-ccw" [size]="13"></lucide-icon>
                  <span>Đặt lại hồ sơ về Cold Start</span>
                </button>
              </div>
            </section>
          </main>
        </div>
      </div>
    </div>
  `,
})
export class ProfilePageComponent implements OnInit {
  readonly profileService = inject(ProfileService);
  private readonly fb = inject(FormBuilder);
  private readonly messageService = inject(MessageService, { optional: true });
  private readonly confirmationService = inject(ConfirmationService, { optional: true });

  readonly profile = this.profileService.profile;
  readonly srlMetrics = this.profileService.srlMetrics;
  readonly selectedCategory = signal<string>('ALL');

  readonly timezoneOptions: TimezoneOption[] = [
    { value: 'Asia/Ho_Chi_Minh', label: 'Asia/Ho_Chi_Minh (Việt Nam)', offset: 'GMT+07:00' },
    { value: 'Asia/Bangkok', label: 'Asia/Bangkok (Thái Lan)', offset: 'GMT+07:00' },
    { value: 'Asia/Singapore', label: 'Asia/Singapore', offset: 'GMT+08:00' },
    { value: 'Asia/Tokyo', label: 'Asia/Tokyo (Nhật Bản)', offset: 'GMT+09:00' },
    { value: 'Asia/Seoul', label: 'Asia/Seoul (Hàn Quốc)', offset: 'GMT+09:00' },
    { value: 'Asia/Shanghai', label: 'Asia/Shanghai (Trung Quốc)', offset: 'GMT+08:00' },
    { value: 'Asia/Hong_Kong', label: 'Asia/Hong_Kong', offset: 'GMT+08:00' },
    { value: 'Europe/London', label: 'Europe/London (Anh Quốc)', offset: 'GMT+00:00' },
    { value: 'Europe/Paris', label: 'Europe/Paris (Pháp)', offset: 'GMT+01:00' },
    { value: 'Europe/Berlin', label: 'Europe/Berlin (Đức)', offset: 'GMT+01:00' },
    { value: 'America/New_York', label: 'America/New_York (Miền Đông Mỹ)', offset: 'GMT-05:00' },
    { value: 'America/Chicago', label: 'America/Chicago (Miền Trung Mỹ)', offset: 'GMT-06:00' },
    { value: 'America/Los_Angeles', label: 'America/Los_Angeles (Thái Bình Dương)', offset: 'GMT-08:00' },
    { value: 'Australia/Sydney', label: 'Australia/Sydney (Úc)', offset: 'GMT+10:00' },
    { value: 'UTC', label: 'UTC (Giờ phối hợp quốc tế)', offset: 'GMT+00:00' },
  ];

  readonly memoryCategories = [
    { id: 'ALL', label: 'Tất cả' },
    { id: 'PROFILE', label: 'Hồ sơ' },
    { id: 'BEHAVIORAL', label: 'Hành vi' },
    { id: 'KNOWLEDGE', label: 'Kiến thức' },
    { id: 'INTERACTION', label: 'Tương tác' },
  ];

  readonly userInitials = computed<string>(() => {
    const name = this.profile()?.full_name?.trim() || '';
    if (!name) return 'FF';
    const parts = name.split(/\s+/);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  });

  readonly filteredMemories = computed<readonly LearnerMemoryResponseDTO[]>(() => {
    const list = this.profileService.learnerMemory();
    const cat = this.selectedCategory();
    if (cat === 'ALL') return list;
    return list.filter((item) => item.category.toUpperCase() === cat);
  });

  profileForm: FormGroup = this.fb.group({
    full_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(100)]],
    timezone: ['Asia/Ho_Chi_Minh', [Validators.required]],
  });

  async ngOnInit(): Promise<void> {
    await this.profileService.loadProfile();
    const current = this.profile();
    if (current) {
      this.profileForm.patchValue({
        full_name: current.full_name,
        timezone: current.timezone || 'Asia/Ho_Chi_Minh',
      });
      this.profileForm.markAsPristine();
    }
    void this.profileService.loadLearnerMemory();
  }

  scrollToSection(event: Event, sectionId: string): void {
    event.preventDefault();
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  async onSaveProfile(): Promise<void> {
    if (this.profileForm.invalid) return;
    const { full_name, timezone } = this.profileForm.value;
    try {
      await this.profileService.updateProfile({
        full_name: full_name.trim(),
        timezone,
      });
      this.profileForm.markAsPristine();
      this.messageService?.add({
        severity: 'success',
        summary: 'Cập nhật thành công',
        detail: 'Thông tin hồ sơ và múi giờ đã được lưu trữ an toàn.',
        life: 4000,
      });
    } catch {
      this.messageService?.add({
        severity: 'error',
        summary: 'Lỗi cập nhật',
        detail: 'Không thể lưu hồ sơ. Vui lòng kiểm tra lại thông tin và kết nối.',
        life: 5000,
      });
    }
  }

  reloadMemory(): void {
    void this.profileService.loadLearnerMemory();
  }

  async onConfirmMemory(id: string): Promise<void> {
    try {
      await this.profileService.updateMemory(id, { action: 'confirm', value: null });
      this.messageService?.add({
        severity: 'success',
        summary: 'Đã xác nhận',
        detail: 'Nhận định học tập đã được đánh dấu tường minh (EXPLICIT).',
        life: 3000,
      });
    } catch {
      this.messageService?.add({
        severity: 'error',
        summary: 'Lỗi',
        detail: 'Không thể xác nhận memory item.',
        life: 4000,
      });
    }
  }

  async onRejectMemory(id: string): Promise<void> {
    try {
      await this.profileService.updateMemory(id, { action: 'reject', value: null });
      this.messageService?.add({
        severity: 'info',
        summary: 'Đã từ chối',
        detail: 'Suy luận AI này sẽ không được đưa vào việc lập lịch học.',
        life: 3000,
      });
    } catch {
      this.messageService?.add({
        severity: 'error',
        summary: 'Lỗi',
        detail: 'Không thể từ chối inference.',
        life: 4000,
      });
    }
  }

  onRequestReset(): void {
    if (this.confirmationService) {
      this.confirmationService.confirm({
        message: 'Bạn có chắc chắn muốn đưa hồ sơ về Cold Start? Tất cả memory và mastery sẽ bị xóa bỏ.',
        header: 'Xác nhận Đặt lại Cold Start',
        icon: 'pi pi-exclamation-triangle',
        acceptLabel: 'Xác nhận xóa',
        rejectLabel: 'Hủy',
        acceptButtonStyleClass: 'p-button-danger',
        accept: () => {
          void this.executeReset();
        },
      });
    } else {
      if (confirm('Bạn có chắc chắn muốn đưa hồ sơ về Cold Start?')) {
        void this.executeReset();
      }
    }
  }

  private async executeReset(): Promise<void> {
    try {
      await this.profileService.resetLearnerMemory();
      this.messageService?.add({
        severity: 'success',
        summary: 'Đã hoàn tất',
        detail: 'Hồ sơ nhận thức đã được đưa về trạng thái Cold Start.',
        life: 4000,
      });
    } catch {
      this.messageService?.add({
        severity: 'error',
        summary: 'Lỗi',
        detail: 'Không thể đặt lại hồ sơ.',
        life: 4000,
      });
    }
  }

  formatValue(value: unknown): string {
    if (!value) return '{}';
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }
    return String(value);
  }
}
