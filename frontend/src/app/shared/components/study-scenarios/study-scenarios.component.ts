import { ChangeDetectionStrategy, Component, computed, model } from '@angular/core';

export interface ScenarioMilestone {
  timeframe: string;
  title: string;
  description: string;
  status: string;
  statusType: 'completed' | 'in-progress' | 'upcoming';
}

export interface StudyScenario {
  id: 'thesis' | 'aws' | 'ai';
  tabTitle: string;
  title: string;
  objective: string;
  durationBadge: string;
  milestones: ScenarioMilestone[];
}

export type ScenarioId = 'thesis' | 'aws' | 'ai';

@Component({
  selector: 'app-study-scenarios',
  standalone: true,
  templateUrl: './study-scenarios.component.html',
  styleUrl: './study-scenarios.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StudyScenariosComponent {
  readonly activeScenario = model<ScenarioId>('thesis');

  readonly scenarios: Record<ScenarioId, StudyScenario> = {
    thesis: {
      id: 'thesis',
      tabTitle: 'Khóa luận Tốt nghiệp CNTT',
      title: 'Kịch bản: Hoàn thành Đồ án Tốt nghiệp & Khóa luận (12 tuần)',
      objective: 'Mục tiêu: Đạt điểm A, kiến trúc sạch, tài liệu chuẩn IEEE',
      durationBadge: 'Thời lượng: 6h/tuần • Tự thích ứng',
      milestones: [
        {
          timeframe: 'Tuần 1 - 4',
          title: 'SRS & Đặc tả Kiến trúc',
          description: 'Xác lập phạm vi đề tài, thiết kế ERD và sơ đồ tuần tự hệ thống.',
          status: 'Đã xong ✓',
          statusType: 'completed',
        },
        {
          timeframe: 'Tuần 5 - 8',
          title: 'Kiến trúc Hexagonal & Core API',
          description: 'Hiện thực hóa domain logic, tích hợp thanh toán và xác thực JWT.',
          status: 'Đang thực thi (Tuần 6)',
          statusType: 'in-progress',
        },
        {
          timeframe: 'Tuần 9 - 12',
          title: 'Kiểm thử tải & Bảo vệ',
          description: 'Viết luận văn, đo lường benchmark K6 và diễn tập phản biện cùng hội đồng.',
          status: 'Dự kiến',
          statusType: 'upcoming',
        },
      ],
    },
    aws: {
      id: 'aws',
      tabTitle: 'Luyện thi AWS Solutions Architect',
      title: 'Kịch bản: Chinh phục chứng chỉ AWS SAA-C03 (8 tuần)',
      objective: 'Mục tiêu: Đạt chứng chỉ SAA-C03 (800+ điểm), làm chủ 40+ dịch vụ cốt lõi',
      durationBadge: 'Thời lượng: 5h/tuần • Phản xạ thực chiến',
      milestones: [
        {
          timeframe: 'Tuần 1 - 3',
          title: 'IAM, VPC & Mạng Đám Mây Toàn Diện',
          description: 'Cấu hình CIDR, Subnet, Route Table, NAT Gateway và Security Group chuẩn Well-Architected.',
          status: 'Đã xong ✓',
          statusType: 'completed',
        },
        {
          timeframe: 'Tuần 4 - 6',
          title: 'Compute, Storage & High Availability',
          description: 'Thiết kế hệ thống Auto Scaling EC2, S3 Tiering, Aurora Serverless v2 và DynamoDB.',
          status: 'Đang thực thi (Tuần 5)',
          statusType: 'in-progress',
        },
        {
          timeframe: 'Tuần 7 - 8',
          title: 'Mock Exam & Tối Ưu Chi Phí (FinOps)',
          description: 'Giải 6 bộ đề thi thử chuẩn Stephane Maarek, tối ưu hóa chi phí và bảo mật multi-account.',
          status: 'Dự kiến',
          statusType: 'upcoming',
        },
      ],
    },
    ai: {
      id: 'ai',
      tabTitle: 'Chuyển ngành AI Engineer',
      title: 'Kịch bản: Chuyển dịch năng lực AI Engineer (12 tuần)',
      objective: 'Mục tiêu: Làm chủ Fine-tuning LLM, kiến trúc RAG nâng cao & Multi-Agent Harness',
      durationBadge: 'Thời lượng: 8h/tuần • Dự án Portfolio',
      milestones: [
        {
          timeframe: 'Tuần 1 - 4',
          title: 'Nền tảng PyTorch, Transformers & Vector DBs',
          description: 'Toán đại số tuyến tính cho Deep Learning, Transformers self-attention, indexing với pgvector & Qdrant.',
          status: 'Đã xong ✓',
          statusType: 'completed',
        },
        {
          timeframe: 'Tuần 5 - 8',
          title: 'Advanced RAG & Multi-Agent Frameworks',
          description: 'Tối ưu Hybrid Search, Re-ranking, Context Compression và xây dựng multi-agent điều phối tuần tự.',
          status: 'Đang thực thi (Tuần 6)',
          statusType: 'in-progress',
        },
        {
          timeframe: 'Tuần 9 - 12',
          title: 'Fine-tuning Llama/Qwen & Production Deployment',
          description: 'LoRA/QLoRA fine-tuning trên custom dataset, vLLM serving, benchmark throughput và đánh giá Hallucination.',
          status: 'Dự kiến',
          statusType: 'upcoming',
        },
      ],
    },
  };

  readonly currentScenario = computed(() => this.scenarios[this.activeScenario()]);

  setScenario(scenario: ScenarioId): void {
    this.activeScenario.set(scenario);
  }
}
