import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
} from '@angular/core';
import { SafeResourceUrl } from '@angular/platform-browser';
import {
  ArrowLeft,
  Check,
  Clock,
  CloudRain,
  Coffee,
  Flame,
  Lock,
  LUCIDE_ICONS,
  LucideAngularModule,
  LucideIconProvider,
  Maximize2,
  Minimize2,
  Music,
  Palette,
  Plus,
  Radio,
  Shield,
  Sparkles,
  Trash2,
  Volume2,
  VolumeX,
  Waves,
  X,
} from 'lucide-angular';
import { WORKSPACE_SCENES } from '../data/workspace-studio.store';
import {
  ClockSize,
  ClockStyleId,
  FocusShieldConfig,
  SoundChannelId,
  SoundChannelState,
  WorkspaceSceneId,
  WorkspaceToolPopover,
} from '../models/workspace.model';

interface ClockStyleOption {
  id: ClockStyleId;
  label: string;
  description: string;
}

const CLOCK_STYLE_OPTIONS: readonly ClockStyleOption[] = [
  {
    id: 'editorial',
    label: 'Editorial Serif',
    description: 'Chữ Newsreader cổ điển',
  },
  {
    id: 'ring',
    label: 'Architectural Ring',
    description: 'Vòng tiến độ tối giản',
  },
  {
    id: 'flip',
    label: 'Flip Clock',
    description: 'Thẻ lật cơ học',
  },
  {
    id: 'minimal',
    label: 'Minimal Digital',
    description: 'Số hiện đại, gọn gàng',
  },
];

@Component({
  selector: 'ff-workspace-tool-panel',
  standalone: true,
  imports: [LucideAngularModule],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        ArrowLeft,
        Check,
        Clock,
        CloudRain,
        Coffee,
        Flame,
        Lock,
        Maximize2,
        Minimize2,
        Music,
        Palette,
        Plus,
        Radio,
        Shield,
        Sparkles,
        Trash2,
        Volume2,
        VolumeX,
        Waves,
        X,
      }),
    },
  ],
  template: `
    @if (activeTool(); as tool) {
      <section
        role="region"
        [attr.aria-label]="toolTitle(tool)"
        class="flex flex-col bg-transparent text-[var(--ws-text-primary,var(--on-surface))]"
      >
        <!-- Compact Inline Header -->
        <header
          class="sticky top-0 z-10 flex items-center justify-between gap-2 border-b border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-lowest))] px-3.5 py-2 backdrop-blur-md"
        >
          <button
            type="button"
            (click)="closePanel.emit()"
            aria-label="Quay lại bảng công cụ"
            class="inline-flex items-center gap-1.5 rounded-[4px] border border-transparent px-1.5 py-1 text-xs font-medium text-[var(--ws-text-muted,var(--on-surface-variant))] transition-colors hover:border-[var(--ws-border,var(--outline-variant))] hover:bg-[var(--ws-surface-control,var(--surface-container-low))] hover:text-[var(--ws-text-primary,var(--on-surface))] cursor-pointer"
          >
            <lucide-icon
              name="arrow-left"
              [size]="14"
              aria-hidden="true"
            ></lucide-icon>
            <span>Quay lại</span>
          </button>

          <h3
            class="m-0 truncate font-serif text-sm font-medium tracking-tight text-[var(--ws-text-primary,var(--on-surface))]"
          >
            {{ toolTitle(tool) }}
          </h3>
        </header>

        <div class="p-3.5">
          <!-- 1. AUDIO CONFIG -->
          @if (tool === 'audio') {
            <div class="flex flex-col gap-3.5">
              <!-- Master Volume & Mute -->
              <div
                class="flex items-center gap-3 rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-low))] px-3 py-2"
              >
                <button
                  type="button"
                  (click)="toggleMute.emit()"
                  [attr.aria-label]="
                    isMuted() ? 'Bật âm thanh' : 'Tắt tiếng tất cả'
                  "
                  [attr.aria-pressed]="isMuted()"
                  class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-lowest))] text-[var(--ws-text-primary,var(--on-surface))] transition-colors hover:border-[var(--ws-accent,var(--primary))] cursor-pointer"
                >
                  <lucide-icon
                    [name]="isMuted() ? 'volume-x' : 'volume-2'"
                    [size]="15"
                    aria-hidden="true"
                  ></lucide-icon>
                </button>
                <div class="flex min-w-0 flex-1 flex-col gap-1">
                  <div class="flex items-center justify-between text-xs">
                    <span
                      class="font-medium text-[var(--ws-text-primary,var(--on-surface))]"
                    >
                      Âm lượng tổng
                    </span>
                    <span
                      class="tabular-nums text-[var(--ws-text-muted,var(--on-surface-variant))]"
                    >
                      {{ isMuted() ? '0%' : masterVolumePercent() + '%' }}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    [value]="masterVolume()"
                    (input)="onMasterVolumeInput($event)"
                    aria-label="Âm lượng tổng"
                    class="h-1.5 w-full accent-[var(--ws-accent,var(--primary))] cursor-pointer"
                  />
                </div>
              </div>

              <!-- Chime & Scene Preset -->
              <div class="flex flex-wrap items-center justify-between gap-2">
                <button
                  type="button"
                  (click)="toggleChime.emit()"
                  [attr.aria-pressed]="chimeEnabled()"
                  class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors cursor-pointer"
                  [class.border-[var(--ws-accent,var(--primary))]]="
                    chimeEnabled()
                  "
                  [class.bg-[var(--ws-surface-control,var(--surface-container-low))]]="
                    chimeEnabled()
                  "
                  [class.text-[var(--ws-accent,var(--primary))]]="
                    chimeEnabled()
                  "
                  [class.border-[var(--ws-border,var(--outline-variant))]]="
                    !chimeEnabled()
                  "
                  [class.text-[var(--ws-text-muted,var(--on-surface-variant))]]="
                    !chimeEnabled()
                  "
                >
                  <lucide-icon
                    name="sparkles"
                    [size]="12"
                    aria-hidden="true"
                  ></lucide-icon>
                  <span>
                    Chuông hết phiên: {{ chimeEnabled() ? 'Bật' : 'Tắt' }}
                  </span>
                </button>

                <button
                  type="button"
                  (click)="applySceneAudio.emit()"
                  class="inline-flex items-center gap-1.5 rounded-full border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-lowest))] px-2.5 py-1 text-[11px] font-medium text-[var(--ws-text-primary,var(--on-surface))] transition-colors hover:border-[var(--ws-accent,var(--primary))] cursor-pointer"
                >
                  <lucide-icon
                    name="palette"
                    [size]="12"
                    aria-hidden="true"
                  ></lucide-icon>
                  <span>Khớp bối cảnh</span>
                </button>
              </div>

              <!-- 5 Ambient Channels -->
              <div class="flex flex-col gap-1.5">
                <span
                  class="text-[11px] font-semibold uppercase tracking-wider text-[var(--ws-text-muted,var(--on-surface-variant))]"
                >
                  Âm thanh nền
                </span>
                @for (ch of channels(); track ch.id) {
                  <div
                    class="flex items-center gap-2.5 rounded-[4px] border px-2.5 py-1.5 transition-colors"
                    [class.border-[var(--ws-accent,var(--primary))]]="
                      ch.active
                    "
                    [class.bg-[var(--ws-surface-control,var(--surface-container-low))]]="
                      ch.active
                    "
                    [class.border-[var(--ws-border,var(--outline-variant))]]="
                      !ch.active
                    "
                  >
                    <button
                      type="button"
                      (click)="toggleChannel.emit(ch.id)"
                      [attr.aria-pressed]="ch.active"
                      [attr.aria-label]="'Bật tắt ' + ch.label"
                      class="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border transition-colors cursor-pointer"
                      [class.border-[var(--ws-accent,var(--primary))]]="
                        ch.active
                      "
                      [class.bg-[var(--ws-accent,var(--primary))]]="
                        ch.active
                      "
                      [class.text-[var(--on-primary)]]="ch.active"
                      [class.border-[var(--ws-border,var(--outline-variant))]]="
                        !ch.active
                      "
                      [class.text-[var(--ws-text-muted,var(--on-surface-variant))]]="
                        !ch.active
                      "
                    >
                      <lucide-icon
                        [name]="channelIcon(ch.id)"
                        [size]="13"
                        aria-hidden="true"
                      ></lucide-icon>
                    </button>
                    <span
                      class="w-20 shrink-0 truncate text-xs font-medium text-[var(--ws-text-primary,var(--on-surface))]"
                    >
                      {{ ch.label }}
                    </span>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      [value]="ch.volume"
                      (input)="onChannelVolumeInput(ch.id, $event)"
                      [attr.aria-label]="'Âm lượng ' + ch.label"
                      class="h-1.5 flex-1 accent-[var(--ws-accent,var(--primary))] cursor-pointer"
                    />
                    <span
                      class="w-8 text-right text-[11px] tabular-nums text-[var(--ws-text-muted,var(--on-surface-variant))]"
                    >
                      {{ Math.round(ch.volume * 100) }}%
                    </span>
                  </div>
                }
              </div>

              <!-- Lo-fi Media Embed -->
              <div
                class="flex flex-col gap-2 border-t border-[var(--ws-border,var(--outline-variant))] pt-3"
              >
                <div class="flex items-center justify-between">
                  <span
                    class="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--ws-text-muted,var(--on-surface-variant))]"
                  >
                    <lucide-icon
                      name="music"
                      [size]="12"
                      aria-hidden="true"
                    ></lucide-icon>
                    Nhạc Lo-fi (YouTube / Spotify)
                  </span>
                  @if (safeEmbedUrl()) {
                    <button
                      type="button"
                      (click)="onClearEmbed()"
                      class="text-xs font-medium text-[var(--error)] hover:underline cursor-pointer"
                    >
                      Gỡ nhạc
                    </button>
                  }
                </div>

                <form
                  (submit)="onSubmitEmbed($event)"
                  class="flex items-center gap-2"
                >
                  <input
                    type="url"
                    [value]="embedDraft()"
                    (input)="onEmbedDraftInput($event)"
                    placeholder="Dán link YouTube hoặc Spotify..."
                    aria-label="Liên kết YouTube hoặc Spotify"
                    class="h-8 min-w-0 flex-1 rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-lowest))] px-2.5 text-xs text-[var(--ws-text-primary,var(--on-surface))] placeholder:text-[var(--ws-text-muted,var(--on-surface-variant))] focus:border-[var(--ws-accent,var(--primary))] focus:outline-none"
                  />
                  <button
                    type="submit"
                    class="h-8 shrink-0 rounded-[4px] bg-[var(--ws-accent,var(--inverse-surface))] px-3 text-xs font-medium text-[var(--on-primary,var(--inverse-on-surface))] transition-opacity hover:opacity-90 cursor-pointer"
                  >
                    Áp dụng
                  </button>
                </form>

                @if (embedError(); as err) {
                  <p role="alert" class="m-0 text-xs text-[var(--error)]">
                    {{ err }}
                  </p>
                }

                @if (safeEmbedUrl(); as url) {
                  <div
                    class="overflow-hidden rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-low))]"
                  >
                    <iframe
                      [src]="url"
                      [title]="
                        embedProvider() === 'spotify'
                          ? 'Trình phát Spotify'
                          : 'Trình phát YouTube'
                      "
                      class="w-full border-0"
                      [style.height]="
                        embedProvider() === 'spotify' ? '152px' : '168px'
                      "
                      sandbox="allow-scripts allow-same-origin allow-presentation"
                      loading="lazy"
                      allow="autoplay; encrypted-media; picture-in-picture"
                    ></iframe>
                  </div>
                }
              </div>
            </div>
          }

          <!-- 2. FOCUS SHIELD CONFIG -->
          @if (tool === 'shield') {
            <div class="flex flex-col gap-3">
              <!-- Focus Score & Distraction Counter -->
              <div
                class="flex items-center justify-between rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-low))] px-3 py-2"
              >
                <div class="flex flex-col">
                  <span
                    class="text-[11px] font-semibold uppercase tracking-wider text-[var(--ws-text-muted,var(--on-surface-variant))]"
                  >
                    Điểm tập trung
                  </span>
                  <span
                    class="text-xs text-[var(--ws-text-muted,var(--on-surface-variant))]"
                  >
                    {{ distractionCount() }} lần rời tab
                  </span>
                </div>
                <span
                  class="inline-flex items-center rounded-full border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-lowest))] px-2.5 py-0.5 text-xs font-semibold tabular-nums text-[var(--ws-accent,var(--primary))]"
                >
                  {{ focusScore() }}/100
                </span>
              </div>

              <!-- Toggles -->
              <div class="flex flex-col gap-1.5">
                <label
                  class="flex items-center justify-between gap-3 rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,transparent)] px-3 py-2 cursor-pointer"
                >
                  <span
                    class="text-xs font-medium text-[var(--ws-text-primary,var(--on-surface))]"
                  >
                    Giám sát rời tab
                  </span>
                  <input
                    type="checkbox"
                    [checked]="shieldConfig().tabGuardEnabled"
                    (change)="
                      toggleTabGuard.emit(!shieldConfig().tabGuardEnabled)
                    "
                    aria-label="Giám sát rời tab"
                    class="h-4 w-4 accent-[var(--ws-accent,var(--primary))] cursor-pointer"
                  />
                </label>

                <label
                  class="flex items-center justify-between gap-3 rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,transparent)] px-3 py-2 cursor-pointer"
                >
                  <div class="flex min-w-0 items-center gap-2">
                    <lucide-icon
                      name="lock"
                      [size]="13"
                      class="shrink-0 text-[var(--ws-text-muted,var(--on-surface-variant))]"
                      aria-hidden="true"
                    ></lucide-icon>
                    <span
                      class="text-xs font-medium text-[var(--ws-text-primary,var(--on-surface))]"
                    >
                      Khóa Tập Trung (Zen + Chống thoát nhầm)
                    </span>
                  </div>
                  <input
                    type="checkbox"
                    [checked]="shieldConfig().zenLockEnabled"
                    (change)="
                      toggleZenLock.emit(!shieldConfig().zenLockEnabled)
                    "
                    aria-label="Khóa Tập Trung"
                    class="h-4 w-4 shrink-0 accent-[var(--ws-accent,var(--primary))] cursor-pointer"
                  />
                </label>

                <button
                  type="button"
                  (click)="toggleFullscreen.emit()"
                  class="flex items-center justify-center gap-2 rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-lowest))] px-3 py-1.5 text-xs font-medium text-[var(--ws-text-primary,var(--on-surface))] transition-colors hover:border-[var(--ws-accent,var(--primary))] cursor-pointer"
                >
                  <lucide-icon
                    [name]="isFullscreen() ? 'minimize-2' : 'maximize-2'"
                    [size]="13"
                    aria-hidden="true"
                  ></lucide-icon>
                  <span>
                    {{
                      isFullscreen() ? 'Thoát toàn màn hình' : 'Toàn màn hình'
                    }}
                  </span>
                </button>
              </div>

              <!-- Sub-tabs -->
              <div
                class="flex rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-low))] p-0.5"
                role="tablist"
              >
                <button
                  type="button"
                  role="tab"
                  [attr.aria-selected]="shieldTab() === 'blocklist'"
                  (click)="shieldTab.set('blocklist')"
                  class="flex-1 rounded-[3px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer"
                  [class.bg-[var(--ws-surface-control,var(--surface-container-lowest))]]="
                    shieldTab() === 'blocklist'
                  "
                  [class.text-[var(--ws-text-primary,var(--on-surface))]]="
                    shieldTab() === 'blocklist'
                  "
                  [class.shadow-xs]="shieldTab() === 'blocklist'"
                  [class.text-[var(--ws-text-muted,var(--on-surface-variant))]]="
                    shieldTab() !== 'blocklist'
                  "
                >
                  Cam kết tránh ({{ shieldConfig().blocklist.length }})
                </button>
                <button
                  type="button"
                  role="tab"
                  [attr.aria-selected]="shieldTab() === 'parking'"
                  (click)="shieldTab.set('parking')"
                  class="flex-1 rounded-[3px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer"
                  [class.bg-[var(--ws-surface-control,var(--surface-container-lowest))]]="
                    shieldTab() === 'parking'
                  "
                  [class.text-[var(--ws-text-primary,var(--on-surface))]]="
                    shieldTab() === 'parking'
                  "
                  [class.shadow-xs]="shieldTab() === 'parking'"
                  [class.text-[var(--ws-text-muted,var(--on-surface-variant))]]="
                    shieldTab() !== 'parking'
                  "
                >
                  Bãi đỗ suy nghĩ ({{ shieldConfig().parkingLot.length }})
                </button>
              </div>

              @if (shieldTab() === 'blocklist') {
                <div class="flex flex-col gap-2">
                  <form
                    (submit)="onSubmitBlockedSite($event)"
                    class="flex items-center gap-2"
                  >
                    <input
                      type="text"
                      [value]="blockedSiteDraft()"
                      (input)="onBlockedSiteInput($event)"
                      placeholder="Ví dụ: facebook.com"
                      aria-label="Thêm trang web cần tránh"
                      class="h-8 min-w-0 flex-1 rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-lowest))] px-2.5 text-xs text-[var(--ws-text-primary,var(--on-surface))] placeholder:text-[var(--ws-text-muted,var(--on-surface-variant))] focus:border-[var(--ws-accent,var(--primary))] focus:outline-none"
                    />
                    <button
                      type="submit"
                      aria-label="Thêm vào danh sách tránh"
                      class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[4px] bg-[var(--ws-accent,var(--inverse-surface))] text-[var(--on-primary,var(--inverse-on-surface))] cursor-pointer"
                    >
                      <lucide-icon
                        name="plus"
                        [size]="14"
                        aria-hidden="true"
                      ></lucide-icon>
                    </button>
                  </form>

                  @if (shieldConfig().blocklist.length === 0) {
                    <p
                      class="m-0 text-xs text-[var(--ws-text-muted,var(--on-surface-variant))]"
                    >
                      Chưa có trang nào trong cam kết tránh.
                    </p>
                  } @else {
                    <div class="flex flex-wrap gap-1.5">
                      @for (site of shieldConfig().blocklist; track site) {
                        <span
                          class="inline-flex items-center gap-1 rounded-full border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-low))] px-2.5 py-0.5 text-xs text-[var(--ws-text-primary,var(--on-surface))]"
                        >
                          <span>{{ site }}</span>
                          <button
                            type="button"
                            (click)="removeBlockedSite.emit(site)"
                            [attr.aria-label]="'Xóa ' + site"
                            class="inline-flex h-4 w-4 items-center justify-center rounded-full text-[var(--ws-text-muted,var(--on-surface-variant))] hover:text-[var(--error)] cursor-pointer"
                          >
                            <lucide-icon
                              name="x"
                              [size]="11"
                              aria-hidden="true"
                            ></lucide-icon>
                          </button>
                        </span>
                      }
                    </div>
                  }
                </div>
              } @else {
                <div class="flex flex-col gap-2">
                  <form
                    (submit)="onSubmitParkingThought($event)"
                    class="flex items-center gap-2"
                  >
                    <input
                      type="text"
                      [value]="parkingDraft()"
                      (input)="onParkingInput($event)"
                      placeholder="Gửi nhanh suy nghĩ chen ngang..."
                      aria-label="Thêm suy nghĩ vào bãi đỗ"
                      class="h-8 min-w-0 flex-1 rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-lowest))] px-2.5 text-xs text-[var(--ws-text-primary,var(--on-surface))] placeholder:text-[var(--ws-text-muted,var(--on-surface-variant))] focus:border-[var(--ws-accent,var(--primary))] focus:outline-none"
                    />
                    <button
                      type="submit"
                      aria-label="Lưu suy nghĩ"
                      class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[4px] bg-[var(--ws-accent,var(--inverse-surface))] text-[var(--on-primary,var(--inverse-on-surface))] cursor-pointer"
                    >
                      <lucide-icon
                        name="plus"
                        [size]="14"
                        aria-hidden="true"
                      ></lucide-icon>
                    </button>
                  </form>

                  @if (shieldConfig().parkingLot.length === 0) {
                    <p
                      class="m-0 text-xs text-[var(--ws-text-muted,var(--on-surface-variant))]"
                    >
                      Đầu óc thoáng đãng. Nếu có việc chợt nhớ ra, hãy đỗ tạm
                      vào đây.
                    </p>
                  } @else {
                    <ul class="m-0 flex list-none flex-col gap-1.5 p-0">
                      @for (item of shieldConfig().parkingLot; track item.id) {
                        <li
                          class="flex items-center justify-between gap-2 rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-low))] px-2.5 py-1.5"
                        >
                          <button
                            type="button"
                            (click)="toggleParkingThought.emit(item.id)"
                            [attr.aria-pressed]="item.done"
                            class="flex min-w-0 flex-1 items-center gap-2 text-left text-xs cursor-pointer"
                          >
                            <span
                              class="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded border"
                              [class.border-[var(--ws-accent,var(--primary))]]="
                                item.done
                              "
                              [class.bg-[var(--ws-accent,var(--primary))]]="
                                item.done
                              "
                              [class.text-[var(--on-primary)]]="item.done"
                              [class.border-[var(--ws-border,var(--outline-variant))]]="
                                !item.done
                              "
                            >
                              @if (item.done) {
                                <lucide-icon
                                  name="check"
                                  [size]="11"
                                  aria-hidden="true"
                                ></lucide-icon>
                              }
                            </span>
                            <span
                              class="truncate text-[var(--ws-text-primary,var(--on-surface))]"
                              [class.line-through]="item.done"
                              [class.opacity-60]="item.done"
                            >
                              {{ item.text }}
                            </span>
                          </button>
                          <button
                            type="button"
                            (click)="removeParkingThought.emit(item.id)"
                            aria-label="Xóa suy nghĩ"
                            class="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[var(--ws-text-muted,var(--on-surface-variant))] hover:text-[var(--error)] cursor-pointer"
                          >
                            <lucide-icon
                              name="trash-2"
                              [size]="12"
                              aria-hidden="true"
                            ></lucide-icon>
                          </button>
                        </li>
                      }
                    </ul>
                  }
                </div>
              }
            </div>
          }

          <!-- 3. SCENES CONFIG -->
          @if (tool === 'scene') {
            <div class="grid grid-cols-1 gap-2">
              @for (item of sceneOptions; track item.id) {
                <button
                  type="button"
                  (click)="selectScene.emit(item.id)"
                  [attr.aria-pressed]="scene() === item.id"
                  class="flex items-center gap-2.5 rounded-[6px] border p-2 text-left transition-colors cursor-pointer"
                  [class.border-[var(--ws-accent,var(--primary))]]="
                    scene() === item.id
                  "
                  [class.bg-[var(--ws-surface-control,var(--surface-container-low))]]="
                    scene() === item.id
                  "
                  [class.border-[var(--ws-border,var(--outline-variant))]]="
                    scene() !== item.id
                  "
                >
                  <span
                    class="relative h-9 w-12 shrink-0 overflow-hidden rounded-[4px] border border-[var(--ws-border,var(--outline-variant))]"
                    [style.background]="item.fallbackGradient"
                  >
                    @if (
                      item.imageUrl &&
                      item.id !== 'architectural' &&
                      !hasThumbError(item.id)
                    ) {
                      <img
                        [src]="item.imageUrl"
                        alt=""
                        loading="lazy"
                        decoding="async"
                        (error)="onThumbError(item.id)"
                        class="h-full w-full object-cover"
                      />
                    }
                  </span>

                  <div class="flex min-w-0 flex-1 flex-col">
                    <span
                      class="truncate text-xs font-semibold text-[var(--ws-text-primary,var(--on-surface))]"
                    >
                      {{ item.label }}
                    </span>
                    <span
                      class="truncate text-[11px] text-[var(--ws-text-muted,var(--on-surface-variant))]"
                    >
                      {{ item.description }}
                    </span>
                  </div>

                  @if (scene() === item.id) {
                    <span
                      class="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--ws-accent,var(--primary))] text-[var(--on-primary)]"
                    >
                      <lucide-icon
                        name="check"
                        [size]="12"
                        aria-hidden="true"
                      ></lucide-icon>
                    </span>
                  }
                </button>
              }
            </div>
          }

          <!-- 4. CLOCK UI CONFIG -->
          @if (tool === 'clock') {
            <div class="flex flex-col gap-3">
              <div class="grid grid-cols-2 gap-1.5">
                @for (opt of clockStyleOptions; track opt.id) {
                  <button
                    type="button"
                    (click)="selectClockStyle.emit(opt.id)"
                    [attr.aria-pressed]="clockStyle() === opt.id"
                    class="flex flex-col items-start gap-0.5 rounded-[4px] border p-2 text-left transition-colors cursor-pointer"
                    [class.border-[var(--ws-accent,var(--primary))]]="
                      clockStyle() === opt.id
                    "
                    [class.bg-[var(--ws-surface-control,var(--surface-container-low))]]="
                      clockStyle() === opt.id
                    "
                    [class.border-[var(--ws-border,var(--outline-variant))]]="
                      clockStyle() !== opt.id
                    "
                  >
                    <span
                      class="text-xs font-semibold text-[var(--ws-text-primary,var(--on-surface))]"
                    >
                      {{ opt.label }}
                    </span>
                    <span
                      class="text-[11px] text-[var(--ws-text-muted,var(--on-surface-variant))]"
                    >
                      {{ opt.description }}
                    </span>
                  </button>
                }
              </div>

              <!-- Size Toggle -->
              <div class="flex items-center justify-between gap-2">
                <span
                  class="text-xs font-medium text-[var(--ws-text-primary,var(--on-surface))]"
                >
                  Kích thước đồng hồ
                </span>
                <div
                  class="inline-flex rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,var(--surface-container-low))] p-0.5"
                >
                  <button
                    type="button"
                    (click)="selectClockSize.emit('md')"
                    [attr.aria-pressed]="clockSize() === 'md'"
                    class="rounded-[3px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer"
                    [class.bg-[var(--ws-surface-control,var(--surface-container-lowest))]]="
                      clockSize() === 'md'
                    "
                    [class.text-[var(--ws-text-primary,var(--on-surface))]]="
                      clockSize() === 'md'
                    "
                    [class.text-[var(--ws-text-muted,var(--on-surface-variant))]]="
                      clockSize() !== 'md'
                    "
                  >
                    Vừa
                  </button>
                  <button
                    type="button"
                    (click)="selectClockSize.emit('lg')"
                    [attr.aria-pressed]="clockSize() === 'lg'"
                    class="rounded-[3px] px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer"
                    [class.bg-[var(--ws-surface-control,var(--surface-container-lowest))]]="
                      clockSize() === 'lg'
                    "
                    [class.text-[var(--ws-text-primary,var(--on-surface))]]="
                      clockSize() === 'lg'
                    "
                    [class.text-[var(--ws-text-muted,var(--on-surface-variant))]]="
                      clockSize() !== 'lg'
                    "
                  >
                    Lớn
                  </button>
                </div>
              </div>

              <!-- Switches -->
              <label
                class="flex items-center justify-between gap-3 rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,transparent)] px-3 py-2 cursor-pointer"
              >
                <span
                  class="text-xs font-medium text-[var(--ws-text-primary,var(--on-surface))]"
                >
                  Hiện giây
                </span>
                <input
                  type="checkbox"
                  [checked]="showSeconds()"
                  (change)="toggleShowSeconds.emit()"
                  aria-label="Hiện giây"
                  class="h-4 w-4 accent-[var(--ws-accent,var(--primary))] cursor-pointer"
                />
              </label>

              <label
                class="flex items-center justify-between gap-3 rounded-[4px] border border-[var(--ws-border,var(--outline-variant))] bg-[var(--ws-surface-control,transparent)] px-3 py-2 cursor-pointer"
              >
                <span
                  class="text-xs font-medium text-[var(--ws-text-primary,var(--on-surface))]"
                >
                  Hiện trên tiêu đề tab
                </span>
                <input
                  type="checkbox"
                  [checked]="showInTabTitle()"
                  (change)="toggleShowInTabTitle.emit()"
                  aria-label="Hiện trên tiêu đề tab"
                  class="h-4 w-4 accent-[var(--ws-accent,var(--primary))] cursor-pointer"
                />
              </label>
            </div>
          }
        </div>
      </section>
    }
  `,
  host: {
    '(document:keydown.escape)': 'onEscapeKey()',
  },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceToolPanelComponent {
  protected readonly Math = Math;
  protected readonly sceneOptions = WORKSPACE_SCENES;
  protected readonly clockStyleOptions = CLOCK_STYLE_OPTIONS;

  // Inputs
  readonly activeTool = input.required<WorkspaceToolPopover>();
  readonly scene = input.required<WorkspaceSceneId>();
  readonly clockStyle = input.required<ClockStyleId>();
  readonly clockSize = input.required<ClockSize>();
  readonly showSeconds = input.required<boolean>();
  readonly showInTabTitle = input.required<boolean>();
  readonly masterVolume = input.required<number>();
  readonly isMuted = input.required<boolean>();
  readonly chimeEnabled = input.required<boolean>();
  readonly channels = input.required<SoundChannelState[]>();
  readonly embedProvider = input<'youtube' | 'spotify' | null>(null);
  readonly safeEmbedUrl = input<SafeResourceUrl | null>(null);
  readonly embedRawInput = input<string>('');
  readonly embedError = input<string | null>(null);
  readonly shieldConfig = input.required<FocusShieldConfig>();
  readonly distractionCount = input<number>(0);
  readonly focusScore = input<number>(100);
  readonly isFullscreen = input<boolean>(false);

  // Outputs
  readonly closePanel = output<void>();
  readonly selectScene = output<WorkspaceSceneId>();
  readonly selectClockStyle = output<ClockStyleId>();
  readonly selectClockSize = output<ClockSize>();
  readonly toggleShowSeconds = output<void>();
  readonly toggleShowInTabTitle = output<void>();
  readonly toggleChannel = output<SoundChannelId>();
  readonly changeChannelVolume = output<{
    id: SoundChannelId;
    volume: number;
  }>();
  readonly changeMasterVolume = output<number>();
  readonly toggleMute = output<void>();
  readonly toggleChime = output<void>();
  readonly applySceneAudio = output<void>();
  readonly applyMediaEmbed = output<string>();
  readonly clearMediaEmbed = output<void>();
  readonly toggleTabGuard = output<boolean>();
  readonly toggleZenLock = output<boolean>();
  readonly toggleFullscreen = output<void>();
  readonly addBlockedSite = output<string>();
  readonly removeBlockedSite = output<string>();
  readonly addParkingThought = output<string>();
  readonly toggleParkingThought = output<string>();
  readonly removeParkingThought = output<string>();

  // Local UI state
  readonly shieldTab = signal<'blocklist' | 'parking'>('blocklist');
  readonly embedDraft = signal<string>('');
  readonly blockedSiteDraft = signal<string>('');
  readonly parkingDraft = signal<string>('');
  private readonly failedThumbIds = signal<ReadonlySet<WorkspaceSceneId>>(
    new Set()
  );

  readonly masterVolumePercent = computed(() =>
    Math.round(this.masterVolume() * 100)
  );

  constructor() {
    effect(() => {
      this.embedDraft.set(this.embedRawInput());
    });
  }

  protected hasThumbError(id: WorkspaceSceneId): boolean {
    return this.failedThumbIds().has(id);
  }

  protected onThumbError(id: WorkspaceSceneId): void {
    this.failedThumbIds.update((prev) => {
      if (prev.has(id)) {
        return prev;
      }
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  }

  protected onEscapeKey(): void {
    if (this.activeTool() !== null) {
      this.closePanel.emit();
    }
  }

  protected toolTitle(tool: Exclude<WorkspaceToolPopover, null>): string {
    switch (tool) {
      case 'audio':
        return 'Âm thanh & Nhạc nền';
      case 'shield':
        return 'Chặn sao nhãng';
      case 'scene':
        return 'Bối cảnh không gian';
      case 'clock':
        return 'Giao diện đồng hồ';
    }
  }

  protected channelIcon(id: SoundChannelId): string {
    switch (id) {
      case 'rain':
        return 'cloud-rain';
      case 'cafe':
        return 'coffee';
      case 'brown':
        return 'waves';
      case 'white':
        return 'radio';
      case 'fireplace':
        return 'flame';
    }
  }

  protected onMasterVolumeInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    const val = Number.parseFloat(target.value);
    if (!Number.isNaN(val)) {
      this.changeMasterVolume.emit(val);
    }
  }

  protected onChannelVolumeInput(id: SoundChannelId, event: Event): void {
    const target = event.target as HTMLInputElement;
    const val = Number.parseFloat(target.value);
    if (!Number.isNaN(val)) {
      this.changeChannelVolume.emit({ id, volume: val });
    }
  }

  protected onEmbedDraftInput(event: Event): void {
    this.embedDraft.set((event.target as HTMLInputElement).value);
  }

  protected onSubmitEmbed(event: Event): void {
    event.preventDefault();
    this.applyMediaEmbed.emit(this.embedDraft().trim());
  }

  protected onClearEmbed(): void {
    this.embedDraft.set('');
    this.clearMediaEmbed.emit();
  }

  protected onBlockedSiteInput(event: Event): void {
    this.blockedSiteDraft.set((event.target as HTMLInputElement).value);
  }

  protected onSubmitBlockedSite(event: Event): void {
    event.preventDefault();
    const site = this.blockedSiteDraft().trim();
    if (!site) {
      return;
    }
    this.addBlockedSite.emit(site);
    this.blockedSiteDraft.set('');
  }

  protected onParkingInput(event: Event): void {
    this.parkingDraft.set((event.target as HTMLInputElement).value);
  }

  protected onSubmitParkingThought(event: Event): void {
    event.preventDefault();
    const text = this.parkingDraft().trim();
    if (!text) {
      return;
    }
    this.addParkingThought.emit(text);
    this.parkingDraft.set('');
  }
}
