import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  computed,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import {
  ArrowRight,
  ExternalLink,
  Globe,
  GripHorizontal,
  LUCIDE_ICONS,
  LucideAngularModule,
  LucideIconProvider,
  Play,
  Trash2,
} from 'lucide-angular';
import {
  extractNoteMediaPreviews,
  NoteMediaPreview,
} from '../data/note-media.util';
import { StickyNoteColor, StickyNoteItem } from '../models/workspace.model';

export interface NoteColorOption {
  id: StickyNoteColor;
  label: string;
  dotClass: string;
  paper: string;
  paperDark: string;
  foldLight: string;
  fold: string;
  tilt: string;
  tapeTilt: string;
}

export const NOTE_COLOR_OPTIONS: readonly NoteColorOption[] = [
  {
    id: 'cream',
    label: 'Màu vàng',
    dotClass: 'bg-[#fff0a6] border-[#e6cf5c]',
    paper: '#fff0a6',
    paperDark: '#fbdd7a',
    foldLight: '#fff8cf',
    fold: '#efd069',
    tilt: '-1.5deg',
    tapeTilt: '-4deg',
  },
  {
    id: 'pink',
    label: 'Màu hồng',
    dotClass: 'bg-[#ffd3de] border-[#e59eb1]',
    paper: '#ffd3de',
    paperDark: '#f8b4c7',
    foldLight: '#ffe7ee',
    fold: '#eb9eb4',
    tilt: '2deg',
    tapeTilt: '3deg',
  },
  {
    id: 'sage',
    label: 'Màu bạc hà',
    dotClass: 'bg-[#cdf2de] border-[#8fd6a8]',
    paper: '#cdf2de',
    paperDark: '#a6e0c0',
    foldLight: '#e3f9ed',
    fold: '#91d1ae',
    tilt: '-1deg',
    tapeTilt: '5deg',
  },
  {
    id: 'blue',
    label: 'Màu xanh dương',
    dotClass: 'bg-[#cfe6ff] border-[#8ebae8]',
    paper: '#cfe6ff',
    paperDark: '#a9cff3',
    foldLight: '#e6f2ff',
    fold: '#95bfe8',
    tilt: '1.5deg',
    tapeTilt: '-3deg',
  },
  {
    id: 'amber',
    label: 'Màu đào',
    dotClass: 'bg-[#ffdfbf] border-[#e8ac74]',
    paper: '#ffdfbf',
    paperDark: '#f9c391',
    foldLight: '#ffeedc',
    fold: '#ebb079',
    tilt: '-2deg',
    tapeTilt: '2deg',
  },
  {
    id: 'lavender',
    label: 'Màu tím oải hương',
    dotClass: 'bg-[#e8dcff] border-[#bfa2f0]',
    paper: '#e8dcff',
    paperDark: '#cfbcf3',
    foldLight: '#f3ecff',
    fold: '#bea8e6',
    tilt: '1.8deg',
    tapeTilt: '-5deg',
  },
];

const NOTE_WIDTH_PX = 220;
const NOTE_MIN_HEIGHT_PX = 210;
const CONTAINER_MARGIN_PX = 12;
const KEYBOARD_NUDGE_PX = 16;
const DRAG_THRESHOLD_PX = 4;

@Component({
  selector: 'ff-workspace-sticky-note-card',
  standalone: true,
  imports: [LucideAngularModule],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        ArrowRight,
        ExternalLink,
        Globe,
        GripHorizontal,
        Play,
        Trash2,
      }),
    },
  ],
  styles: `
    .note {
      position: relative;
      isolation: isolate;
      min-height: 210px;
      transform: rotate(var(--tilt, -1.5deg));
      transition:
        transform 0.45s cubic-bezier(0.22, 1, 0.36, 1),
        filter 0.45s ease;
      filter:
        drop-shadow(0 1px 2px rgba(70, 50, 30, 0.12))
        drop-shadow(0 14px 18px rgba(70, 50, 30, 0.15));
    }

    .note::before {
      content: '';
      position: absolute;
      top: -12px;
      left: 50%;
      width: 82px;
      height: 24px;
      margin-left: -41px;
      transform: rotate(var(--tape, -4deg));
      background: repeating-linear-gradient(
        90deg,
        rgba(255, 252, 242, 0.78) 0 8px,
        rgba(255, 252, 242, 0.62) 8px 16px
      );
      border-radius: 6px;
      box-shadow: 0 1px 2px rgba(70, 50, 30, 0.1);
      pointer-events: none;
      z-index: 2;
    }

    .note::after {
      content: '';
      position: absolute;
      right: 0;
      bottom: 0;
      width: 26px;
      height: 26px;
      background: linear-gradient(
        135deg,
        var(--fold-light, #fff8cf) 0%,
        var(--fold, #efd069) 50%,
        transparent 50.5%
      );
      border-radius: 0 8px 0 8px;
      filter: drop-shadow(-2px -2px 3px rgba(70, 50, 30, 0.16));
      pointer-events: none;
      z-index: 2;
    }

    .note:hover,
    .note:focus-within,
    .note.is-dragging {
      transform: rotate(0deg) translateY(-6px) scale(1.02);
    }

    .note.is-dragging {
      transition: filter 0.15s ease;
      cursor: grabbing;
      user-select: none;
    }

    .paper {
      --ink: #34425f;
      --ink-soft: #5d6a86;
      --grain: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120' viewBox='0 0 120 120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='matrix' values='0 0 0 0 0.25 0 0 0 0 0.18 0 0 0 0 0.12 0 0 0 0.045 0'/%3E%3C/filter%3E%3Crect width='120' height='120' filter='url(%23n)'/%3E%3C/svg%3E");
      height: 100%;
      min-height: 210px;
      padding: 32px 20px 28px;
      border-radius: 16px;
      font-family: 'Patrick Hand', 'Geist', cursive, sans-serif;
      color: var(--ink);
      background:
        var(--grain),
        linear-gradient(180deg, rgba(255, 255, 255, 0.55) 0, rgba(255, 255, 255, 0) 45%),
        linear-gradient(165deg, var(--paper) 55%, var(--paper-dark) 140%);
      clip-path: polygon(
        0 0,
        100% 0,
        100% calc(100% - 26px),
        calc(100% - 26px) 100%,
        0 100%
      );
    }

    @media (prefers-reduced-motion: reduce) {
      .note {
        transform: none !important;
        transition: none !important;
      }

      .note:hover,
      .note:focus-within,
      .note.is-dragging {
        transform: none !important;
      }
    }
  `,
  template: `
    <article
      #cardEl
      [attr.data-note-id]="note().id"
      (pointerdown)="onPointerDown($event)"
      class="note group"
      [class.w-[220px]]="draggableMode()"
      [class.w-full]="!draggableMode()"
      [class.pointer-events-auto]="draggableMode()"
      [class.cursor-grab]="draggableMode() && !isDragging()"
      [class.is-dragging]="isDragging()"
      [style.position]="draggableMode() ? 'absolute' : 'relative'"
      [style.left.px]="draggableMode() ? resolvedPosition().x : null"
      [style.top.px]="draggableMode() ? resolvedPosition().y : null"
      [style.z-index]="draggableMode() ? (note().zIndex ?? index() + 1) : null"
      [style.--paper]="palette().paper"
      [style.--paper-dark]="palette().paperDark"
      [style.--fold-light]="palette().foldLight"
      [style.--fold]="palette().fold"
      [style.--tilt]="palette().tilt"
      [style.--tape]="palette().tapeTilt"
    >
      <!-- Washi-tape Unpin Hit Target -->
      <button
        type="button"
        (click)="unpin.emit(note().id)"
        aria-label="Bỏ ghim ghi chú"
        title="Bỏ ghim ghi chú"
        class="absolute -top-3 left-1/2 z-10 flex h-6 w-[82px] -translate-x-1/2 items-center justify-center rounded-md border-0 bg-transparent p-0 text-[10px] font-medium text-[#34425f] opacity-0 transition-opacity group-hover:opacity-85 focus:opacity-100 cursor-pointer"
      >
        <span class="rounded bg-white/75 px-1.5 py-0.5 leading-none shadow-xs">Bỏ ghim</span>
      </button>

      <div class="paper flex flex-col gap-1.5">
        <!-- Keyboard-accessible Drag Handle (Desktop) -->
        @if (draggableMode()) {
          <div
            role="button"
            tabindex="0"
            aria-label="Kéo để di chuyển ghi chú"
            title="Kéo hoặc dùng phím mũi tên để di chuyển"
            (keydown)="onDragHandleKeyDown($event)"
            class="mx-auto -mt-2 flex h-3.5 w-10 items-center justify-center rounded-full opacity-0 transition-opacity group-hover:opacity-65 focus:opacity-95 focus:outline-none focus:ring-1 focus:ring-[#34425f]/40 cursor-grab active:cursor-grabbing"
            style="color: var(--ink-soft);"
          >
            <lucide-icon name="grip-horizontal" [size]="12" aria-hidden="true"></lucide-icon>
          </div>
        }

        <!-- Editable Title -->
        <input
          type="text"
          data-testid="pinned-note-title-input"
          [value]="note().title"
          (input)="onTitleInput($event)"
          placeholder="Chưa có tiêu đề"
          aria-label="Tiêu đề ghi chú"
          class="w-full border-0 bg-transparent p-0 text-[18px] font-normal leading-snug placeholder:opacity-55 focus:outline-none"
          style="color: var(--ink);"
        />

        <!-- Click-to-edit inline content -->
        @if (isEditing()) {
          <div class="space-y-1.5">
            <textarea
              rows="3"
              [value]="note().content"
              (input)="onContentInput($event)"
              (keydown.escape)="stopEdit.emit()"
              placeholder="Nội dung ghi chú..."
              aria-label="Nội dung ghi chú"
              class="w-full resize-y border-0 bg-transparent p-0 text-[15px] leading-relaxed placeholder:opacity-60 focus:outline-none"
              style="color: var(--ink);"
            ></textarea>
            <div class="flex justify-end">
              <button
                type="button"
                (click)="stopEdit.emit()"
                class="rounded bg-[#34425f]/10 px-2 py-0.5 font-sans text-[11px] font-medium hover:opacity-85 cursor-pointer"
                style="color: var(--ink);"
              >
                Xong
              </button>
            </div>
          </div>
        } @else {
          <div
            role="button"
            tabindex="0"
            (click)="onContentClick()"
            (keydown.enter)="startEdit.emit(note().id)"
            aria-label="Nhấn để chỉnh sửa nội dung ghi chú"
            class="min-h-[2.25rem] whitespace-pre-wrap break-words text-[15px] leading-relaxed cursor-text"
            [style.color]="note().content ? 'var(--ink)' : 'var(--ink-soft)'"
          >
            {{ note().content || 'Nhấn để viết nội dung...' }}
          </div>
        }

        <!-- Rich Media Previews -->
        @if (previews().length > 0) {
          <div class="flex flex-col gap-1.5 font-sans" data-testid="note-media-previews">
            @for (item of previews(); track item.url) {
              @switch (item.kind) {
                @case ('youtube') {
                  <a
                    [href]="item.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="group relative block overflow-hidden rounded-lg border border-black/10 bg-black/20 no-underline"
                  >
                    <img
                      [src]="item.thumbnailUrl"
                      alt="YouTube thumbnail"
                      loading="lazy"
                      class="h-24 w-full object-cover transition-transform duration-200 group-hover:scale-[1.02]"
                    />
                    <div class="absolute inset-0 flex items-center justify-center bg-black/25 transition-colors group-hover:bg-black/35">
                      <span class="inline-flex h-8 w-8 items-center justify-center rounded-full bg-red-600 text-white shadow-md">
                        <lucide-icon name="play" [size]="14" aria-hidden="true"></lucide-icon>
                      </span>
                    </div>
                    <span class="absolute bottom-1 left-1 rounded bg-black/75 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                      YouTube
                    </span>
                  </a>
                }
                @case ('image') {
                  @if (!isMediaFailed(item.url)) {
                    <a
                      [href]="item.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="block overflow-hidden rounded-lg border border-black/10"
                    >
                      <img
                        [src]="item.url"
                        [alt]="item.domain"
                        loading="lazy"
                        (error)="markMediaFailed(item.url)"
                        class="max-h-28 w-full rounded-lg object-cover"
                      />
                    </a>
                  } @else {
                    <a
                      [href]="item.url"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="flex items-center justify-between gap-2 rounded-lg border border-black/10 bg-white/45 px-2 py-1 text-[11px] no-underline hover:opacity-85"
                      style="color: var(--ink);"
                    >
                      <span class="flex min-w-0 items-center gap-1.5">
                        <lucide-icon name="globe" [size]="12" class="shrink-0 opacity-75" aria-hidden="true"></lucide-icon>
                        <span class="truncate font-medium">{{ item.domain }}</span>
                      </span>
                      <lucide-icon name="external-link" [size]="11" class="shrink-0 opacity-70" aria-hidden="true"></lucide-icon>
                    </a>
                  }
                }
                @case ('video') {
                  <video
                    controls
                    preload="metadata"
                    class="max-h-28 w-full rounded-lg bg-black/20"
                  >
                    <source [src]="item.url" />
                  </video>
                }
                @case ('link') {
                  <a
                    [href]="item.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="flex items-center justify-between gap-2 rounded-lg border border-black/10 bg-white/45 px-2 py-1 text-[11px] no-underline transition-opacity hover:opacity-85"
                    style="color: var(--ink);"
                  >
                    <span class="flex min-w-0 items-center gap-1.5">
                      @if (!isMediaFailed(item.faviconUrl)) {
                        <img
                          [src]="item.faviconUrl"
                          [alt]="item.domain"
                          loading="lazy"
                          (error)="markMediaFailed(item.faviconUrl)"
                          class="h-3.5 w-3.5 shrink-0 rounded-sm"
                        />
                      } @else {
                        <lucide-icon name="globe" [size]="13" class="shrink-0 opacity-75" aria-hidden="true"></lucide-icon>
                      }
                      <span class="min-w-0 flex-1">
                        <span class="block truncate font-semibold leading-tight">{{ item.domain }}</span>
                        @if (item.displayPath) {
                          <span
                            class="block truncate text-[10px] leading-tight"
                            style="color: var(--ink-soft);"
                          >
                            {{ item.displayPath }}
                          </span>
                        }
                      </span>
                    </span>
                    <lucide-icon name="external-link" [size]="11" class="shrink-0 opacity-70" aria-hidden="true"></lucide-icon>
                  </a>
                }
              }
            }
          </div>
        }

        <!-- Card Footer (hidden at rest, visible on hover or focus-within) -->
        <footer class="mt-auto flex flex-wrap items-center justify-between gap-1 pt-1.5 font-sans opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100 focus-within:opacity-100">
          <div class="flex items-center gap-1" role="group" aria-label="Đổi màu ghi chú">
            @for (colorOpt of colorOptions; track colorOpt.id) {
              <button
                type="button"
                (click)="changeColor.emit({ id: note().id, color: colorOpt.id })"
                [attr.aria-label]="colorOpt.label"
                [attr.aria-pressed]="note().color === colorOpt.id"
                class="h-3 w-3 rounded-full border transition-transform cursor-pointer"
                [class]="colorOpt.dotClass"
                [class.ring-2]="note().color === colorOpt.id"
                [class.ring-[#34425f]]="note().color === colorOpt.id"
              ></button>
            }
          </div>

          <div class="flex items-center gap-1">
            @if (hasActiveSession()) {
              <button
                type="button"
                (click)="copyToTakeaway.emit(note())"
                class="inline-flex items-center gap-0.5 rounded-full border border-[#34425f]/15 bg-[#34425f]/8 px-1.5 py-0.5 text-[10px] font-medium transition-opacity hover:opacity-85 cursor-pointer"
                style="color: var(--ink);"
              >
                <span>Takeaway</span>
                <lucide-icon name="arrow-right" [size]="9" aria-hidden="true"></lucide-icon>
              </button>
            }

            <button
              type="button"
              (click)="deleteNote.emit(note().id)"
              aria-label="Xóa ghi chú"
              title="Xóa"
              class="inline-flex h-5 w-5 items-center justify-center rounded-full transition-colors hover:bg-[#34425f]/10 hover:text-red-600 cursor-pointer"
              style="color: var(--ink-soft);"
            >
              <lucide-icon name="trash-2" [size]="11" aria-hidden="true"></lucide-icon>
            </button>
          </div>
        </footer>
      </div>
    </article>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceStickyNoteCardComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly cardEl = viewChild<ElementRef<HTMLElement>>('cardEl');

  protected readonly colorOptions = NOTE_COLOR_OPTIONS;

  readonly note = input.required<StickyNoteItem>();
  readonly index = input<number>(0);
  readonly isEditing = input<boolean>(false);
  readonly hasActiveSession = input<boolean>(false);
  readonly draggableMode = input<boolean>(false);
  readonly containerWidth = input<number>(1280);
  readonly containerHeight = input<number>(760);

  readonly unpin = output<string>();
  readonly updateNote = output<{ id: string; title?: string; content?: string }>();
  readonly changeColor = output<{ id: string; color: StickyNoteColor }>();
  readonly deleteNote = output<string>();
  readonly copyToTakeaway = output<StickyNoteItem>();
  readonly startEdit = output<string>();
  readonly stopEdit = output<void>();
  readonly bringToFront = output<string>();
  readonly moveNote = output<{ id: string; posX: number; posY: number }>();

  protected readonly isDragging = signal<boolean>(false);
  private readonly liveDragPos = signal<{ x: number; y: number } | null>(null);
  private readonly failedMediaUrls = signal<ReadonlySet<string>>(new Set());

  private suppressNextClick = false;
  private activeCleanup: (() => void) | null = null;

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.activeCleanup?.();
      this.activeCleanup = null;
    });
  }

  protected readonly palette = computed<NoteColorOption>(() => {
    const color = this.note().color;
    return NOTE_COLOR_OPTIONS.find((opt) => opt.id === color) ?? NOTE_COLOR_OPTIONS[0];
  });

  protected readonly previews = computed<NoteMediaPreview[]>(() =>
    extractNoteMediaPreviews(this.note().content)
  );

  protected readonly resolvedPosition = computed<{ x: number; y: number }>(() => {
    const live = this.liveDragPos();
    if (live) {
      return live;
    }

    const current = this.note();
    const { width, height } = this.getBoundsSize();
    if (
      typeof current.posX === 'number' &&
      Number.isFinite(current.posX) &&
      typeof current.posY === 'number' &&
      Number.isFinite(current.posY)
    ) {
      return this.clampPosition(current.posX, current.posY, width, height);
    }

    const idx = this.index();
    const defaultX = width - 246 - (idx % 2) * 22;
    const defaultY = 68 + idx * 140;
    return this.clampPosition(defaultX, defaultY, width, height);
  });

  protected isMediaFailed(url: string): boolean {
    return this.failedMediaUrls().has(url);
  }

  protected markMediaFailed(url: string): void {
    this.failedMediaUrls.update((prev) => {
      if (prev.has(url)) {
        return prev;
      }
      const next = new Set(prev);
      next.add(url);
      return next;
    });
  }

  protected onTitleInput(event: Event): void {
    const title = (event.target as HTMLInputElement).value;
    this.updateNote.emit({ id: this.note().id, title });
  }

  protected onContentInput(event: Event): void {
    const content = (event.target as HTMLTextAreaElement).value;
    this.updateNote.emit({ id: this.note().id, content });
  }

  protected onContentClick(): void {
    if (this.suppressNextClick) {
      this.suppressNextClick = false;
      return;
    }
    this.startEdit.emit(this.note().id);
  }

  protected onPointerDown(event: PointerEvent): void {
    if (!this.draggableMode()) {
      return;
    }
    if (event.pointerType === 'mouse' && event.button !== 0) {
      return;
    }

    const target = event.target as HTMLElement | null;
    if (target?.closest('input, textarea, button, a, video')) {
      return;
    }

    const noteId = this.note().id;
    this.bringToFront.emit(noteId);

    const startClientX = event.clientX;
    const startClientY = event.clientY;
    const startPos = this.resolvedPosition();
    let hasMoved = false;
    let latestPos = startPos;

    this.activeCleanup?.();

    const onPointerMove = (moveEvent: PointerEvent): void => {
      const dx = moveEvent.clientX - startClientX;
      const dy = moveEvent.clientY - startClientY;
      if (!hasMoved && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) {
        return;
      }
      if (!hasMoved) {
        hasMoved = true;
        this.isDragging.set(true);
      }

      const { width, height } = this.getBoundsSize();
      latestPos = this.clampPosition(
        startPos.x + dx,
        startPos.y + dy,
        width,
        height
      );
      this.liveDragPos.set(latestPos);
    };

    const onPointerUp = (): void => {
      cleanup();
      this.isDragging.set(false);
      this.liveDragPos.set(null);
      if (hasMoved) {
        this.suppressNextClick = true;
        queueMicrotask(() => {
          this.suppressNextClick = false;
        });
        this.moveNote.emit({
          id: noteId,
          posX: latestPos.x,
          posY: latestPos.y,
        });
      }
    };

    const cleanup = (): void => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('pointermove', onPointerMove);
        window.removeEventListener('pointerup', onPointerUp);
        window.removeEventListener('pointercancel', onPointerUp);
      }
      this.activeCleanup = null;
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('pointermove', onPointerMove);
      window.addEventListener('pointerup', onPointerUp);
      window.addEventListener('pointercancel', onPointerUp);
      this.activeCleanup = cleanup;
    }
  }

  protected onDragHandleKeyDown(event: KeyboardEvent): void {
    if (!this.draggableMode()) {
      return;
    }

    let dx = 0;
    let dy = 0;
    switch (event.key) {
      case 'ArrowLeft':
        dx = -KEYBOARD_NUDGE_PX;
        break;
      case 'ArrowRight':
        dx = KEYBOARD_NUDGE_PX;
        break;
      case 'ArrowUp':
        dy = -KEYBOARD_NUDGE_PX;
        break;
      case 'ArrowDown':
        dy = KEYBOARD_NUDGE_PX;
        break;
      default:
        return;
    }

    event.preventDefault();
    const noteId = this.note().id;
    this.bringToFront.emit(noteId);
    const current = this.resolvedPosition();
    const { width, height } = this.getBoundsSize();
    const next = this.clampPosition(
      current.x + dx,
      current.y + dy,
      width,
      height
    );
    this.moveNote.emit({
      id: noteId,
      posX: next.x,
      posY: next.y,
    });
  }

  private getBoundsSize(): { width: number; height: number } {
    const parent = this.cardEl()?.nativeElement.offsetParent as HTMLElement | null;
    const measuredW = parent?.clientWidth ?? 0;
    const measuredH = parent?.clientHeight ?? 0;
    return {
      width: measuredW > 0 ? measuredW : this.containerWidth(),
      height: measuredH > 0 ? measuredH : this.containerHeight(),
    };
  }

  private clampPosition(
    x: number,
    y: number,
    containerWidth: number,
    containerHeight: number
  ): { x: number; y: number } {
    const maxX = Math.max(CONTAINER_MARGIN_PX, containerWidth - (NOTE_WIDTH_PX + CONTAINER_MARGIN_PX));
    const maxY = Math.max(CONTAINER_MARGIN_PX, containerHeight - (NOTE_MIN_HEIGHT_PX + 14));
    return {
      x: Math.round(Math.max(CONTAINER_MARGIN_PX, Math.min(x, maxX))),
      y: Math.round(Math.max(CONTAINER_MARGIN_PX, Math.min(y, maxY))),
    };
  }
}
