import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
  signal,
} from '@angular/core';
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Layers,
  LUCIDE_ICONS,
  LucideAngularModule,
  LucideIconProvider,
  Pin,
  PinOff,
  RotateCcw,
  Trash2,
  X,
} from 'lucide-angular';
import { StickyNoteColor, StickyNoteItem } from '../models/workspace.model';
import {
  NOTE_COLOR_OPTIONS,
  WorkspaceStickyNoteCardComponent,
} from './workspace-sticky-note-card.component';

@Component({
  selector: 'ff-workspace-sticky-notes-panel',
  standalone: true,
  imports: [LucideAngularModule, WorkspaceStickyNoteCardComponent],
  providers: [
    {
      provide: LUCIDE_ICONS,
      multi: true,
      useValue: new LucideIconProvider({
        AlertTriangle,
        ChevronDown,
        ChevronUp,
        Layers,
        Pin,
        PinOff,
        RotateCcw,
        Trash2,
        X,
      }),
    },
  ],
  template: `
    <section
      aria-label="Ghi chú Studio"
      class="flex w-full flex-col gap-3 font-sans"
      style="color: var(--ws-text-primary, var(--on-surface));"
    >
      <!-- Undo Notice Bar -->
      @if (undoNotice(); as notice) {
        <div
          role="status"
          class="flex items-center justify-between gap-2 rounded-xl px-3.5 py-2 text-xs shadow-sm"
          style="background: var(--ws-surface-panel, var(--surface-container-lowest)); border: 1px solid var(--ws-border, var(--outline-variant)); color: var(--ws-text-primary, var(--on-surface)); backdrop-filter: var(--ws-panel-blur, blur(16px));"
        >
          <span class="truncate">{{ notice.message }}</span>
          <button
            type="button"
            (click)="undoAction.emit()"
            class="inline-flex shrink-0 items-center gap-1 rounded-full border border-[var(--ws-border,var(--outline-variant))] px-2.5 py-0.5 text-[11px] font-semibold transition-opacity hover:opacity-80 cursor-pointer"
            style="color: var(--ws-accent, var(--primary));"
          >
            <lucide-icon name="rotate-ccw" [size]="11" aria-hidden="true"></lucide-icon>
            <span>Hoàn tác</span>
          </button>
        </div>
      }

      <!-- Over-limit Non-destructive Warning Banner -->
      @if (isOverLimit()) {
        <div
          role="alert"
          class="flex items-start gap-2 rounded-xl border border-amber-500/50 bg-amber-50/90 px-3.5 py-2.5 text-xs text-amber-950 dark:bg-amber-950/75 dark:text-amber-100"
        >
          <lucide-icon name="alert-triangle" [size]="15" class="mt-0.5 shrink-0" aria-hidden="true"></lucide-icon>
          <div class="min-w-0 flex-1 leading-relaxed">
            <span>Vượt giới hạn đồng bộ 10.000 ký tự — ghi chú vẫn lưu an toàn trên máy</span>
            <span class="ml-1.5 font-mono text-[11px] opacity-80">({{ formattedLength() }})</span>
          </div>
        </div>
      }

      <!-- 1. Note Composer (ONLY when composerOpen() is true) -->
      @if (composerOpen()) {
        <article
          aria-label="Soạn ghi chú mới"
          class="flex flex-col gap-2.5 rounded-xl p-3.5 shadow-sm transition-colors"
          style="background: var(--ws-surface-panel, var(--surface-container-lowest)); border: 1px solid var(--ws-border, var(--outline-variant)); color: var(--ws-text-primary, var(--on-surface)); backdrop-filter: var(--ws-panel-blur, blur(16px));"
        >
          <header class="flex items-center justify-between gap-2">
            <div class="flex items-center gap-2">
              <h2 class="m-0 font-serif text-sm font-medium">Ghi chú mới</h2>
              <span
                class="text-[11px]"
                style="color: var(--ws-text-secondary, var(--on-surface-variant));"
              >
                {{ syncStatusLabel() }}
              </span>
            </div>

            <button
              type="button"
              (click)="closeComposer.emit()"
              aria-label="Đóng khung soạn ghi chú"
              class="inline-flex h-6 w-6 items-center justify-center rounded-full opacity-75 transition-opacity hover:opacity-100 cursor-pointer"
            >
              <lucide-icon name="x" [size]="14" aria-hidden="true"></lucide-icon>
            </button>
          </header>

          <input
            type="text"
            data-testid="scratchpad-title-input"
            [value]="composerTitle()"
            (input)="onComposerTitleInput($event)"
            placeholder="Tiêu đề ghi chú (tùy chọn)..."
            aria-label="Tiêu đề ghi chú mới"
            class="w-full rounded-lg border border-[var(--ws-border,var(--outline-variant))] bg-transparent px-2.5 py-1.5 font-serif text-xs font-semibold placeholder:font-sans placeholder:font-normal placeholder:opacity-60 focus:border-[var(--ws-accent,var(--primary))] focus:outline-none"
            style="color: var(--ws-text-primary, var(--on-surface));"
          />

          <textarea
            rows="3"
            data-testid="scratchpad-textarea"
            [value]="composerContent()"
            (input)="onComposerInput($event)"
            (keydown.enter)="onComposerEnter($event)"
            placeholder="Viết ý tưởng, công thức hoặc câu hỏi... (Enter để ghim, Shift+Enter xuống dòng)"
            aria-label="Nội dung ghi chú mới"
            class="w-full resize-y rounded-lg border border-[var(--ws-border,var(--outline-variant))] bg-transparent p-2.5 text-xs leading-relaxed placeholder:opacity-60 focus:border-[var(--ws-accent,var(--primary))] focus:outline-none"
            style="color: var(--ws-text-primary, var(--on-surface));"
          ></textarea>

          <footer class="flex items-center justify-between gap-2">
            <!-- 6 Color Dots -->
            <div class="flex items-center gap-1.5" role="group" aria-label="Chọn màu giấy ghi chú">
              @for (colorOpt of colorOptions; track colorOpt.id) {
                <button
                  type="button"
                  (click)="composerColor.set(colorOpt.id)"
                  [attr.aria-label]="colorOpt.label"
                  [attr.aria-pressed]="composerColor() === colorOpt.id"
                  class="h-4 w-4 rounded-full border transition-transform cursor-pointer"
                  [class]="colorOpt.dotClass"
                  [class.ring-2]="composerColor() === colorOpt.id"
                  [class.ring-[var(--ws-accent,var(--primary))]]="composerColor() === colorOpt.id"
                  [class.ring-offset-1]="composerColor() === colorOpt.id"
                ></button>
              }
            </div>

            <button
              type="button"
              (click)="submitComposer()"
              [disabled]="!canSubmitComposer()"
              aria-label="Ghim ghi chú lên màn hình"
              class="inline-flex items-center gap-1.5 rounded-full px-3.5 py-1 text-xs font-medium text-[var(--on-primary)] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-45 cursor-pointer"
              style="background: var(--ws-accent, var(--primary));"
            >
              <lucide-icon name="pin" [size]="12" aria-hidden="true"></lucide-icon>
              <span>Ghim</span>
            </button>
          </footer>
        </article>
      }

      <!-- 2. Mobile/Tablet Stacked Pinned Notes (< lg only; Desktop renders floating notes in Studio overlay) -->
      @if (displayedPinnedNotes().length > 0) {
        <div
          class="grid grid-cols-1 gap-3.5 pt-2 sm:grid-cols-2 lg:hidden"
          aria-label="Ghi chú đã ghim trên Studio"
        >
          @for (note of displayedPinnedNotes(); track note.id; let idx = $index) {
            <ff-workspace-sticky-note-card
              [note]="note"
              [index]="idx"
              [isEditing]="editingNoteId() === note.id"
              [hasActiveSession]="hasActiveSession()"
              [draggableMode]="false"
              (unpin)="unpinNote.emit($event)"
              (updateNote)="updateNote.emit($event)"
              (changeColor)="changeColor.emit($event)"
              (deleteNote)="deleteNote.emit($event)"
              (copyToTakeaway)="copyToTakeaway.emit($event)"
              (startEdit)="startEditing($event)"
              (stopEdit)="stopEditing()"
            />
          }
        </div>
      }

      <!-- 3. Note Collection Drawer Toggle & Drawer (only visible while composer is open) -->
      @if (composerOpen() && hasCollectionOverflow()) {
        <div class="flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <button
              type="button"
              (click)="toggleCollectionDrawer()"
              [attr.aria-expanded]="collectionDrawerOpen()"
              class="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-opacity hover:opacity-90 cursor-pointer"
              style="background: var(--ws-surface-panel, var(--surface-container-lowest)); border: 1px solid var(--ws-border, var(--outline-variant)); color: var(--ws-text-primary, var(--on-surface)); backdrop-filter: var(--ws-panel-blur, blur(16px));"
            >
              <lucide-icon name="layers" [size]="12" aria-hidden="true"></lucide-icon>
              <span>Tất cả ghi chú ({{ collectionNotes().length }})</span>
              <lucide-icon
                [name]="collectionDrawerOpen() ? 'chevron-up' : 'chevron-down'"
                [size]="12"
                aria-hidden="true"
              ></lucide-icon>
            </button>
          </div>

          @if (collectionDrawerOpen()) {
            <div
              role="region"
              aria-label="Kho lưu trữ tất cả ghi chú"
              class="max-h-[34vh] space-y-2 overflow-y-auto rounded-xl p-3"
              style="background: var(--ws-surface-panel, var(--surface-container-lowest)); border: 1px solid var(--ws-border, var(--outline-variant)); color: var(--ws-text-primary, var(--on-surface)); backdrop-filter: var(--ws-panel-blur, blur(16px));"
            >
              @for (note of collectionNotes(); track note.id) {
                @let isEditingDrawer = editingNoteId() === note.id;
                <div class="flex flex-col gap-1.5 rounded-lg border border-[var(--ws-border,var(--outline-variant))] p-2.5">
                  <div class="flex items-start justify-between gap-2">
                    @if (isEditingDrawer) {
                      <input
                        type="text"
                        [value]="note.title"
                        (input)="onTitleInput(note.id, $event)"
                        placeholder="Tiêu đề..."
                        aria-label="Tiêu đề ghi chú"
                        class="min-w-0 flex-1 border-0 border-b border-[var(--ws-border,var(--outline-variant))] bg-transparent pb-0.5 font-serif text-xs font-semibold focus:outline-none"
                      />
                    } @else {
                      <button
                        type="button"
                        (click)="startEditing(note.id)"
                        class="min-w-0 flex-1 truncate text-left font-serif text-xs font-semibold hover:underline cursor-pointer bg-transparent border-0 p-0"
                      >
                        {{ note.title || 'Ghi chú không tiêu đề' }}
                      </button>
                    }

                    <div class="flex shrink-0 items-center gap-1">
                      @if (note.pinned) {
                        <button
                          type="button"
                          (click)="unpinNote.emit(note.id)"
                          aria-label="Bỏ ghim"
                          title="Bỏ ghim"
                          class="inline-flex items-center gap-1 rounded-full border border-[var(--ws-border,var(--outline-variant))] px-2 py-0.5 text-[10px] font-medium cursor-pointer"
                        >
                          <lucide-icon name="pin-off" [size]="10" aria-hidden="true"></lucide-icon>
                          <span>Bỏ ghim</span>
                        </button>
                      } @else {
                        <button
                          type="button"
                          (click)="pinNote.emit(note.id)"
                          aria-label="Ghim lên Studio"
                          title="Ghim lên Studio"
                          class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium text-[var(--on-primary)] cursor-pointer"
                          style="background: var(--ws-accent, var(--primary));"
                        >
                          <lucide-icon name="pin" [size]="10" aria-hidden="true"></lucide-icon>
                          <span>Ghim</span>
                        </button>
                      }

                      <button
                        type="button"
                        (click)="deleteNote.emit(note.id)"
                        aria-label="Xóa ghi chú"
                        class="inline-flex h-6 w-6 items-center justify-center rounded-full opacity-75 hover:text-[var(--error)] hover:opacity-100 cursor-pointer"
                      >
                        <lucide-icon name="trash-2" [size]="12" aria-hidden="true"></lucide-icon>
                      </button>
                    </div>
                  </div>

                  @if (isEditingDrawer) {
                    <div class="space-y-1">
                      <textarea
                        rows="2"
                        [value]="note.content"
                        (input)="onContentInput(note.id, $event)"
                        (keydown.escape)="stopEditing()"
                        aria-label="Nội dung ghi chú"
                        class="w-full resize-y rounded border border-[var(--ws-border,var(--outline-variant))] bg-transparent p-1.5 text-xs leading-relaxed focus:outline-none"
                      ></textarea>
                      <div class="flex justify-end">
                        <button
                          type="button"
                          (click)="stopEditing()"
                          class="rounded border border-[var(--ws-border,var(--outline-variant))] px-2 py-0.5 text-[10px] font-medium cursor-pointer"
                        >
                          Xong
                        </button>
                      </div>
                    </div>
                  } @else {
                    <p
                      role="button"
                      tabindex="0"
                      (click)="startEditing(note.id)"
                      (keydown.enter)="startEditing(note.id)"
                      class="m-0 line-clamp-2 text-xs leading-relaxed opacity-85 cursor-text"
                    >
                      {{ note.content || 'Trống' }}
                    </p>
                  }
                </div>
              }
            </div>
          }
        </div>
      }
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspaceStickyNotesPanelComponent {
  protected readonly colorOptions = NOTE_COLOR_OPTIONS;

  readonly composerOpen = input.required<boolean>();
  readonly visiblePinnedNotes = input.required<StickyNoteItem[]>();
  readonly collectionNotes = input.required<StickyNoteItem[]>();
  readonly hasActiveSession = input<boolean>(false);
  readonly heartbeatStatus = input<'idle' | 'syncing' | 'synced' | 'offline' | 'error'>('idle');
  readonly serializedLength = input<number>(0);
  readonly isOverLimit = input<boolean>(false);
  readonly undoNotice = input<{ message: string } | null>(null);

  readonly closeComposer = output<void>();
  readonly pinNewNote = output<{ title: string; content: string; color: StickyNoteColor }>();
  readonly updateNote = output<{ id: string; title?: string; content?: string }>();
  readonly unpinNote = output<string>();
  readonly pinNote = output<string>();
  readonly changeColor = output<{ id: string; color: StickyNoteColor }>();
  readonly deleteNote = output<string>();
  readonly copyToTakeaway = output<StickyNoteItem>();
  readonly undoAction = output<void>();

  readonly composerTitle = signal<string>('');
  readonly composerContent = signal<string>('');
  readonly composerColor = signal<StickyNoteColor>('cream');
  readonly editingNoteId = signal<string | null>(null);
  readonly collectionDrawerOpen = signal<boolean>(false);

  protected readonly canSubmitComposer = computed(
    () => this.composerContent().trim().length > 0
  );

  protected readonly displayedPinnedNotes = computed(() =>
    this.visiblePinnedNotes().slice(0, 4)
  );

  protected readonly hasCollectionOverflow = computed(() => {
    const collection = this.collectionNotes();
    const pinnedCount = this.displayedPinnedNotes().length;
    return collection.length > pinnedCount || collection.some((n) => !n.pinned);
  });

  protected readonly formattedLength = computed(() =>
    this.serializedLength().toLocaleString('vi-VN')
  );

  protected readonly syncStatusLabel = computed(() => {
    switch (this.heartbeatStatus()) {
      case 'syncing':
        return 'Đang đồng bộ...';
      case 'synced':
        return 'Đã đồng bộ phiên học';
      case 'offline':
        return 'Lưu cục bộ (ngoại tuyến)';
      case 'error':
        return 'Lỗi đồng bộ, đã lưu cục bộ';
      case 'idle':
        return this.hasActiveSession() ? 'Sẵn sàng đồng bộ' : 'Lưu tự động cục bộ';
    }
  });

  protected onComposerTitleInput(event: Event): void {
    const target = event.target as HTMLInputElement | null;
    this.composerTitle.set(target?.value ?? '');
  }

  protected onComposerInput(event: Event): void {
    const target = event.target as HTMLTextAreaElement | null;
    this.composerContent.set(target?.value ?? '');
  }

  protected onComposerEnter(event: Event): void {
    const keyEvent = event as KeyboardEvent;
    if (keyEvent.isComposing || keyEvent.keyCode === 229 || keyEvent.shiftKey) {
      return;
    }
    keyEvent.preventDefault();
    this.submitComposer();
  }

  protected submitComposer(): void {
    const content = this.composerContent().trim();
    if (!content) {
      return;
    }
    const title = this.composerTitle().trim();
    this.pinNewNote.emit({ title, content, color: this.composerColor() });
    this.composerTitle.set('');
    this.composerContent.set('');
  }

  protected startEditing(noteId: string): void {
    this.editingNoteId.set(noteId);
  }

  protected stopEditing(): void {
    this.editingNoteId.set(null);
  }

  protected toggleCollectionDrawer(): void {
    this.collectionDrawerOpen.update((v) => !v);
  }

  protected onTitleInput(id: string, event: Event): void {
    const title = (event.target as HTMLInputElement).value;
    this.updateNote.emit({ id, title });
  }

  protected onContentInput(id: string, event: Event): void {
    const content = (event.target as HTMLTextAreaElement).value;
    this.updateNote.emit({ id, content });
  }
}
