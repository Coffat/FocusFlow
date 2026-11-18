import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  computed,
  effect,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { WORKSPACE_SCENES } from '../data/workspace-studio.store';
import { SceneMeta, WorkspaceSceneId } from '../models/workspace.model';

interface RainDrop {
  x: number;
  y: number;
  length: number;
  speed: number;
  opacity: number;
}

@Component({
  selector: 'ff-workspace-scene-backdrop',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    class: 'pointer-events-none absolute inset-0 overflow-hidden select-none',
    'aria-hidden': 'true',
  },
  styles: `
    .ff-arch-grid {
      background-color: var(--surface);
      background-image:
        radial-gradient(var(--outline-variant) 1px, transparent 1px),
        linear-gradient(
          to right,
          color-mix(in srgb, var(--outline-variant) 22%, transparent) 1px,
          transparent 1px
        ),
        linear-gradient(
          to bottom,
          color-mix(in srgb, var(--outline-variant) 22%, transparent) 1px,
          transparent 1px
        );
      background-size: 24px 24px;
    }
  `,
  template: `
    @if (scene() === 'architectural') {
      <div class="absolute inset-0 bg-[var(--surface)]"></div>
      <div class="ff-arch-grid absolute inset-0 opacity-35"></div>
    } @else {
      @let meta = sceneMeta();
      <div
        class="absolute inset-0"
        [style.background]="meta.fallbackGradient"
      ></div>

      @if (meta.imageUrl && !hasImageError(meta.id)) {
        <img
          [src]="meta.imageUrl"
          decoding="async"
          loading="eager"
          alt=""
          (error)="onImageError(meta.id)"
          class="absolute inset-0 h-full w-full object-cover transition-opacity duration-500"
        />
      }

      <div
        class="absolute inset-0"
        [style.background]="meta.scrimRgba"
      ></div>

      @if (scene() === 'rain') {
        <canvas
          #rainCanvas
          class="absolute inset-0 block h-full w-full opacity-75"
        ></canvas>
      }
    }

    <div
      class="absolute inset-0 transition-opacity duration-300"
      [class.bg-black/30]="zenDimmed()"
      [class.opacity-100]="zenDimmed()"
      [class.opacity-0]="!zenDimmed()"
    ></div>
  `,
})
export class WorkspaceSceneBackdropComponent {
  private readonly destroyRef = inject(DestroyRef);

  readonly scene = input.required<WorkspaceSceneId>();
  readonly zenDimmed = input<boolean>(false);

  protected readonly sceneMeta = computed<SceneMeta>(
    () =>
      WORKSPACE_SCENES.find((item) => item.id === this.scene()) ??
      WORKSPACE_SCENES[0]
  );

  private readonly failedSceneIds = signal<ReadonlySet<WorkspaceSceneId>>(
    new Set()
  );

  private readonly rainCanvasRef =
    viewChild<ElementRef<HTMLCanvasElement>>('rainCanvas');

  private rafId: number | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private visibilityCleanup: (() => void) | null = null;

  constructor() {
    effect(() => {
      const currentScene = this.scene();
      const canvasEl = this.rainCanvasRef()?.nativeElement ?? null;

      this.cleanupRainAnimation();

      if (currentScene === 'rain' && canvasEl) {
        this.startRainAnimation(canvasEl);
      }
    });

    this.destroyRef.onDestroy(() => {
      this.cleanupRainAnimation();
    });
  }

  protected hasImageError(id: WorkspaceSceneId): boolean {
    return this.failedSceneIds().has(id);
  }

  protected onImageError(id: WorkspaceSceneId): void {
    this.failedSceneIds.update((prev) => {
      if (prev.has(id)) {
        return prev;
      }
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  }

  private startRainAnimation(canvas: HTMLCanvasElement): void {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return;
    }

    const prefersReducedMotion =
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReducedMotion) {
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = 0;
    let height = 0;
    const drops: RainDrop[] = [];

    const seedDrops = (w: number, h: number): void => {
      drops.length = 0;
      const count = Math.min(72, Math.max(24, Math.floor((w * h) / 22000)));
      for (let i = 0; i < count; i++) {
        drops.push({
          x: Math.random() * w,
          y: Math.random() * h,
          length: 10 + Math.random() * 14,
          speed: 4.5 + Math.random() * 4.5,
          opacity: 0.14 + Math.random() * 0.24,
        });
      }
    };

    const updateCanvasSize = (): void => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      const nextWidth = Math.max(
        1,
        Math.floor(rect?.width ?? canvas.clientWidth ?? 800)
      );
      const nextHeight = Math.max(
        1,
        Math.floor(rect?.height ?? canvas.clientHeight ?? 600)
      );
      if (nextWidth === width && nextHeight === height) return;
      width = nextWidth;
      height = nextHeight;
      canvas.width = width;
      canvas.height = height;
      seedDrops(width, height);
    };

    const drawFrame = (advance: boolean): void => {
      ctx.clearRect(0, 0, width, height);
      ctx.lineWidth = 1;
      ctx.lineCap = 'round';

      for (const drop of drops) {
        ctx.strokeStyle = `rgba(186, 214, 240, ${drop.opacity})`;
        ctx.beginPath();
        ctx.moveTo(drop.x, drop.y);
        ctx.lineTo(drop.x - 1.5, drop.y + drop.length);
        ctx.stroke();

        if (advance) {
          drop.y += drop.speed;
          drop.x -= 0.45;
          if (drop.y > height + drop.length) {
            drop.y = -drop.length;
            drop.x = Math.random() * (width + 20);
          }
        }
      }
    };

    updateCanvasSize();

    if (typeof ResizeObserver !== 'undefined' && canvas.parentElement) {
      this.resizeObserver = new ResizeObserver(() => {
        updateCanvasSize();
        if (document.hidden) {
          drawFrame(false);
        }
      });
      this.resizeObserver.observe(canvas.parentElement);
    }

    const tick = (): void => {
      if (document.hidden) {
        this.rafId = null;
        return;
      }
      drawFrame(true);
      this.rafId = window.requestAnimationFrame(tick);
    };

    const onVisibilityChange = (): void => {
      if (document.hidden) {
        if (this.rafId !== null) {
          window.cancelAnimationFrame(this.rafId);
          this.rafId = null;
        }
      } else if (this.rafId === null) {
        this.rafId = window.requestAnimationFrame(tick);
      }
    };

    document.addEventListener('visibilitychange', onVisibilityChange);
    this.visibilityCleanup = () => {
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };

    if (!document.hidden) {
      this.rafId = window.requestAnimationFrame(tick);
    }
  }

  private cleanupRainAnimation(): void {
    if (this.rafId !== null && typeof window !== 'undefined') {
      window.cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
    if (this.visibilityCleanup) {
      this.visibilityCleanup();
      this.visibilityCleanup = null;
    }
  }
}
