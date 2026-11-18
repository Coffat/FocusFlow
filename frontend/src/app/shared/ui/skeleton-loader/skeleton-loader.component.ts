import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type SkeletonVariant = 'card' | 'bento' | 'text' | 'timeline';

@Component({
  selector: 'app-skeleton-loader',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './skeleton-loader.component.scss',
  template: `
    <div
      role="status"
      aria-busy="true"
      aria-live="polite"
      aria-label="Đang tải dữ liệu..."
      [style.height]="height()"
      class="w-full"
    >
      <span class="sr-only">Đang tải dữ liệu...</span>

      @switch (variant()) {
        @case ('bento') {
          <div class="grid grid-cols-1 md:grid-cols-12 gap-5 w-full">
            <!-- Bento 1: 7 cols -->
            <div class="md:col-span-7 rounded-xl p-6 md:p-8 bg-white border border-outline-variant/30 flex flex-col justify-between min-h-[300px]">
              <div>
                <div class="w-9 h-9 rounded-lg skeleton-shimmer mb-5"></div>
                <div class="h-6 w-3/4 rounded skeleton-shimmer mb-3"></div>
                <div class="h-4 w-full rounded skeleton-shimmer mb-2"></div>
                <div class="h-4 w-5/6 rounded skeleton-shimmer mb-6"></div>
              </div>
              <div class="h-16 w-full rounded-lg skeleton-shimmer"></div>
            </div>

            <!-- Bento 2: 5 cols -->
            <div class="md:col-span-5 rounded-xl p-6 md:p-8 bg-white border border-outline-variant/30 flex flex-col justify-between min-h-[300px]">
              <div>
                <div class="w-9 h-9 rounded-lg skeleton-shimmer mb-5"></div>
                <div class="h-6 w-2/3 rounded skeleton-shimmer mb-3"></div>
                <div class="h-4 w-full rounded skeleton-shimmer mb-2"></div>
                <div class="h-4 w-4/5 rounded skeleton-shimmer mb-6"></div>
              </div>
              <div class="h-14 w-full rounded-lg skeleton-shimmer"></div>
            </div>

            <!-- Bento 3: 5 cols -->
            <div class="md:col-span-5 rounded-xl p-6 md:p-8 bg-white border border-outline-variant/30 flex flex-col justify-between min-h-[300px]">
              <div>
                <div class="w-9 h-9 rounded-lg skeleton-shimmer mb-5"></div>
                <div class="h-6 w-3/4 rounded skeleton-shimmer mb-3"></div>
                <div class="h-4 w-full rounded skeleton-shimmer mb-2"></div>
                <div class="h-4 w-2/3 rounded skeleton-shimmer mb-6"></div>
              </div>
              <div class="h-14 w-full rounded-lg skeleton-shimmer"></div>
            </div>

            <!-- Bento 4: 7 cols -->
            <div class="md:col-span-7 rounded-xl p-6 md:p-8 bg-white border border-outline-variant/30 flex flex-col justify-between min-h-[300px]">
              <div>
                <div class="w-9 h-9 rounded-lg skeleton-shimmer mb-5"></div>
                <div class="h-6 w-2/3 rounded skeleton-shimmer mb-3"></div>
                <div class="h-4 w-full rounded skeleton-shimmer mb-2"></div>
                <div class="h-4 w-5/6 rounded skeleton-shimmer mb-6"></div>
              </div>
              <div class="h-20 w-full rounded-lg skeleton-shimmer"></div>
            </div>
          </div>
        }

        @case ('timeline') {
          <div class="rounded-xl p-6 md:p-8 bg-white border border-outline-variant/30 w-full min-h-[360px]">
            <div class="flex items-center justify-between pb-6 border-b border-outline-variant/20 mb-8">
              <div class="space-y-2">
                <div class="h-5 w-64 rounded skeleton-shimmer"></div>
                <div class="h-3.5 w-80 rounded skeleton-shimmer"></div>
              </div>
              <div class="h-6 w-36 rounded-full skeleton-shimmer"></div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              @for (item of repeatArray(); track $index) {
                <div class="p-5 rounded-lg border border-outline-variant/30 bg-surface-container-low/20 flex flex-col justify-between min-h-[170px]">
                  <div>
                    <div class="flex justify-between items-center mb-3">
                      <div class="h-4 w-16 rounded skeleton-shimmer"></div>
                      <div class="w-4 h-4 rounded-full skeleton-shimmer"></div>
                    </div>
                    <div class="h-4 w-3/4 rounded skeleton-shimmer mb-2"></div>
                    <div class="h-3.5 w-full rounded skeleton-shimmer"></div>
                  </div>
                  <div class="h-4 w-20 rounded skeleton-shimmer mt-4 pt-3 border-t border-outline-variant/20"></div>
                </div>
              }
            </div>
          </div>
        }

        @case ('text') {
          <div class="space-y-2.5 w-full">
            @for (item of repeatArray(); track $index) {
              <div class="h-4 rounded skeleton-shimmer" [style.width]="($index % 2 === 0 ? '100%' : '75%')"></div>
            }
          </div>
        }

        @default {
          <!-- Card variant (e.g. 3 testimonial cards) -->
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
            @for (item of repeatArray(); track $index) {
              <div class="rounded-xl p-6 bg-white border border-outline-variant/30 flex flex-col justify-between min-h-[220px]">
                <div class="space-y-2 mb-6">
                  <div class="h-4 w-full rounded skeleton-shimmer"></div>
                  <div class="h-4 w-11/12 rounded skeleton-shimmer"></div>
                  <div class="h-4 w-4/5 rounded skeleton-shimmer"></div>
                </div>
                <div class="flex items-center gap-3 pt-4 border-t border-outline-variant/20">
                  <div class="w-9 h-9 rounded-full skeleton-shimmer shrink-0"></div>
                  <div class="space-y-1.5 w-full">
                    <div class="h-3.5 w-24 rounded skeleton-shimmer"></div>
                    <div class="h-3 w-32 rounded skeleton-shimmer"></div>
                  </div>
                </div>
              </div>
            }
          </div>
        }
      }
    </div>
  `,
})
export class SkeletonLoaderComponent {
  readonly variant = input<SkeletonVariant>('card');
  readonly height = input<string | undefined>(undefined);
  readonly count = input<number>(3);

  readonly repeatArray = computed(() => Array.from({ length: Math.max(1, this.count()) }));
}
