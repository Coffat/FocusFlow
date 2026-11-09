import {
  DestroyRef,
  Directive,
  ElementRef,
  OnInit,
  PLATFORM_ID,
  Renderer2,
  inject,
  input,
  numberAttribute,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export type RevealDirection = 'up' | 'down' | 'left' | 'right' | 'none';

@Directive({
  selector: '[appScrollReveal]',
  standalone: true,
})
export class ScrollRevealDirective implements OnInit {
  private readonly el = inject(ElementRef);
  private readonly renderer = inject(Renderer2);
  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);

  readonly revealDelay = input<number, unknown>(0, { transform: numberAttribute });
  readonly revealDirection = input<RevealDirection>('up');

  private observer: IntersectionObserver | null = null;

  ngOnInit(): void {
    const nativeElement = this.el.nativeElement as HTMLElement;

    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    // Accessible prefers-reduced-motion check
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (prefersReducedMotion || typeof IntersectionObserver === 'undefined') {
      this.renderer.addClass(nativeElement, 'is-revealed');
      this.renderer.setStyle(nativeElement, 'opacity', '1');
      this.renderer.setStyle(nativeElement, 'transform', 'none');
      return;
    }

    // Set initial unrevealed styles
    const initialTransform = this.getInitialTransform(this.revealDirection());
    const delay = Math.max(0, this.revealDelay());

    this.renderer.setStyle(nativeElement, 'opacity', '0');
    if (initialTransform !== 'none') {
      this.renderer.setStyle(nativeElement, 'transform', initialTransform);
    }
    this.renderer.setStyle(
      nativeElement,
      'transition',
      'opacity 0.65s cubic-bezier(0.16, 1, 0.3, 1), transform 0.65s cubic-bezier(0.16, 1, 0.3, 1)'
    );
    if (delay > 0) {
      this.renderer.setStyle(nativeElement, 'transitionDelay', `${delay}ms`);
    }
    this.renderer.setStyle(nativeElement, 'willChange', 'opacity, transform');

    this.initObserver(nativeElement);

    this.destroyRef.onDestroy(() => {
      this.cleanupObserver();
    });
  }

  private initObserver(element: HTMLElement): void {
    this.observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            this.reveal(element);
            break;
          }
        }
      },
      {
        threshold: 0.12,
        rootMargin: '0px 0px -30px 0px',
      }
    );

    this.observer.observe(element);
  }

  reveal(element?: HTMLElement): void {
    const target = element ?? (this.el.nativeElement as HTMLElement);
    this.renderer.addClass(target, 'is-revealed');
    this.renderer.setStyle(target, 'opacity', '1');
    const revealedTransform = this.getRevealedTransform(this.revealDirection());
    this.renderer.setStyle(target, 'transform', revealedTransform);
    this.cleanupObserver();
  }

  private cleanupObserver(): void {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
  }

  private getRevealedTransform(direction: RevealDirection): string {
    switch (direction) {
      case 'up':
      case 'down':
        return 'translateY(0)';
      case 'left':
      case 'right':
        return 'translateX(0)';
      case 'none':
        return 'none';
      default:
        return 'translateY(0)';
    }
  }

  private getInitialTransform(direction: RevealDirection): string {
    switch (direction) {
      case 'up':
        return 'translateY(28px)';
      case 'down':
        return 'translateY(-28px)';
      case 'left':
        return 'translateX(28px)';
      case 'right':
        return 'translateX(-28px)';
      case 'none':
        return 'none';
      default:
        return 'translateY(28px)';
    }
  }
}
