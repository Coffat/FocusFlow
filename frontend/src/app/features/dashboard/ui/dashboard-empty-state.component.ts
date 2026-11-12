import { Component, ChangeDetectionStrategy, output } from '@angular/core';
import {
  BlueprintEmptyStateComponent,
  StarterTemplate,
} from '../../../shared/components/blueprint-empty-state/blueprint-empty-state.component';

@Component({
  selector: 'app-dashboard-empty-state',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BlueprintEmptyStateComponent],
  template: `
    <app-blueprint-empty-state
      title="Chưa có lộ trình học tập nào"
      description="Hãy bắt đầu bằng cách mô tả mục tiêu học tập hoặc tài liệu bạn muốn chinh phục. AI Harness sẽ phân tích, chia nhỏ thành các cột mốc và tự động tối ưu hóa theo quỹ thời gian của bạn."
      ctaLabel="Tạo Lộ trình Học tập Đầu tiên với AI"
      ctaRoute="/roadmaps"
      shortcutKey="C"
      (selectTemplate)="onSelectTemplate($event)"
      (createCustomRoadmap)="onCreateCustom()"
    />
  `,
})
export class DashboardEmptyStateComponent {
  readonly selectTemplate = output<StarterTemplate>();
  readonly createCustomRoadmap = output<void>();

  onSelectTemplate(tpl: StarterTemplate): void {
    this.selectTemplate.emit(tpl);
  }

  onCreateCustom(): void {
    this.createCustomRoadmap.emit();
  }
}
