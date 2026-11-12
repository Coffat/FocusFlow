import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { CommonModule } from '@angular/common';

export interface StarterTemplate {
  id: string;
  title: string;
  subtitle: string;
  categoryTag: string;
  weeksCount: number;
  tasksCount: number;
  knowledgeLevel?: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED';
  hoursPerWeek?: number;
  tags: string[];
}

export const DEFAULT_STARTER_TEMPLATES: StarterTemplate[] = [
  {
    id: 'fastapi-microservices',
    title: 'FastAPI & Microservices',
    subtitle:
      'Chinh phục Ports & Adapters, Asyncpg, Taskiq và triển khai Docker theo chuẩn kiến trúc sạch.',
    categoryTag: 'Backend',
    weeksCount: 12,
    tasksCount: 84,
    knowledgeLevel: 'INTERMEDIATE',
    hoursPerWeek: 12,
    tags: ['Backend', 'Python', 'Hexagonal Architecture'],
  },
  {
    id: 'aws-solutions-architect',
    title: 'AWS Solutions Architect',
    subtitle:
      'Làm chủ VPC, IAM, ECS Fargate, S3, RDS và thiết kế hệ thống đám mây High Availability.',
    categoryTag: 'Cloud Arch',
    weeksCount: 8,
    tasksCount: 56,
    knowledgeLevel: 'BEGINNER',
    hoursPerWeek: 8,
    tags: ['Cloud Arch', 'DevOps', 'AWS'],
  },
  {
    id: 'ielts-academic-75',
    title: 'IELTS Academic Band 7.5',
    subtitle:
      'Rèn phản xạ Writing Task 2 và Speaking Part 3 theo chuẩn học thuật chuyên sâu và phương pháp Monastic.',
    categoryTag: 'Academic',
    weeksCount: 10,
    tasksCount: 70,
    knowledgeLevel: 'INTERMEDIATE',
    hoursPerWeek: 10,
    tags: ['Academic', 'IELTS', 'Writing & Speaking'],
  },
];

@Component({
  selector: 'app-blueprint-empty-state',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './blueprint-empty-state.component.html',
  styleUrl: './blueprint-empty-state.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BlueprintEmptyStateComponent {
  readonly title = input<string>('Chưa có lộ trình học tập nào');
  readonly description = input<string>(
    'Hãy bắt đầu hành trình tự học thích ứng bằng cách mô tả mục tiêu của bạn. FocusFlow sẽ phân rã thành các Milestone và đồng bộ thời khóa biểu tự động.'
  );
  readonly templates = input<StarterTemplate[]>(DEFAULT_STARTER_TEMPLATES);
  readonly showTemplates = input<boolean>(true);
  readonly ctaLabel = input<string>('Tạo lộ trình học tập');
  readonly ctaRoute = input<string>('/roadmaps/new');
  readonly shortcutKey = input<string>('C');

  readonly selectTemplate = output<StarterTemplate>();
  readonly createCustomRoadmap = output<void>();

  onSelectTemplate(tpl: StarterTemplate): void {
    this.selectTemplate.emit(tpl);
  }

  onCreateCustom(): void {
    this.createCustomRoadmap.emit();
  }
}
