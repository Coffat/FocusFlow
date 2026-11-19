import { ChangeDetectionStrategy, Component, computed, model } from '@angular/core';

export interface ScenarioSampleTask {
  title: string;
  duration: string;
  dependency?: string;
}

export interface ScenarioMilestone {
  timeframe: string;
  title: string;
  description: string;
  effortLabel: string;
  deliverable: string;
  sampleTasks: ScenarioSampleTask[];
  status: string;
  statusType: 'completed' | 'in-progress' | 'upcoming';
}

export interface StudyScenario {
  id: 'thesis' | 'aws' | 'ai';
  tabTitle: string;
  title: string;
  objective: string;
  durationBadge: string;
  availabilityMode: string;
  totalEffortHours: string;
  feasibilityStatus: string;
  ragSources: string[];
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
      availabilityMode: 'Mode B: T2–T6 (19:30–21:30) • T7 (09:00–11:30)',
      totalEffortHours: '72 giờ',
      feasibilityStatus: 'Khả thi • Tải 78% quỹ giờ rảnh',
      ragSources: ['SRS & ADR Specs', 'Official Docs'],
      milestones: [
        {
          timeframe: 'Tuần 1 - 4',
          title: 'SRS & Đặc tả Kiến trúc',
          description: 'Xác lập phạm vi đề tài, thiết kế ERD 3NF và sơ đồ tuần tự hệ thống.',
          effortLabel: '24 giờ • 16 blocks',
          deliverable: 'Prove Mode: Phản biện đặc tả SRS & ERD',
          sampleTasks: [
            { title: 'Phân rã Use Case & Ràng buộc nghiệp vụ', duration: '90m' },
            { title: 'Thiết kế ERD chuẩn 3NF & Index', duration: '120m', dependency: 'Sau Use Case' },
          ],
          status: 'Đã xong ✓',
          statusType: 'completed',
        },
        {
          timeframe: 'Tuần 5 - 8',
          title: 'Kiến trúc Hexagonal & Core API',
          description: 'Hiện thực hóa domain logic, kiểm soát IDOR và xác thực cookie JWT.',
          effortLabel: '28 giờ • 20 blocks',
          deliverable: 'Prove Mode: Kiểm thử Domain & API',
          sampleTasks: [
            { title: 'Cài đặt Aggregate & AsyncUnitOfWork', duration: '90m', dependency: 'Sau ERD 3NF' },
            { title: 'Kiểm thử tích hợp Router & Outbox', duration: '60m', dependency: 'Sau Aggregate' },
          ],
          status: 'Đang thực thi (Tuần 6)',
          statusType: 'in-progress',
        },
        {
          timeframe: 'Tuần 9 - 12',
          title: 'Kiểm thử tải & Bảo vệ',
          description: 'Hoàn thiện luận văn, đo benchmark K6 và diễn tập phản biện cùng hội đồng.',
          effortLabel: '20 giờ • 14 blocks',
          deliverable: 'Prove Mode: Diễn tập Demo & Q&A Hội đồng',
          sampleTasks: [
            { title: 'Chạy kịch bản tải K6 & tối ưu query', duration: '90m', dependency: 'Sau Core API' },
            { title: 'Tổng hợp Key Takeaways & Slide bảo vệ', duration: '60m' },
          ],
          status: 'Dự kiến',
          statusType: 'upcoming',
        },
      ],
    },
    aws: {
      id: 'aws',
      tabTitle: 'Luyện thi AWS Solutions Architect',
      title: 'Kịch bản: Chinh phục chứng chỉ AWS SAA-C03 (8 tuần)',
      objective: 'Mục tiêu: Đạt chứng chỉ SAA-C03 (800+ điểm), làm chủ kiến trúc Well-Architected',
      durationBadge: 'Thời lượng: 5h/tuần • Mode A Linh hoạt',
      availabilityMode: 'Mode A: Mục tiêu 5 giờ/tuần • Phân bổ linh hoạt',
      totalEffortHours: '40 giờ',
      feasibilityStatus: 'Khả thi • Dư 12% đệm dự phòng',
      ragSources: ['AWS SAA-C03 Exam Guide', 'Well-Architected Docs'],
      milestones: [
        {
          timeframe: 'Tuần 1 - 3',
          title: 'IAM, VPC & Mạng Đám Mây Toàn Diện',
          description: 'Cấu hình CIDR, Subnet, Route Table, NAT Gateway và Security Group đa tầng.',
          effortLabel: '15 giờ • 10 blocks',
          deliverable: 'Prove Mode: Lab thiết kế VPC Multi-AZ',
          sampleTasks: [
            { title: 'Chia dải CIDR & Public/Private Subnet', duration: '60m' },
            { title: 'Thực hành IAM Policy & Least Privilege', duration: '90m', dependency: 'Sau VPC' },
          ],
          status: 'Đã xong ✓',
          statusType: 'completed',
        },
        {
          timeframe: 'Tuần 4 - 6',
          title: 'Compute, Storage & High Availability',
          description: 'Thiết kế Auto Scaling EC2, S3 Tiering, Aurora Serverless v2 và DynamoDB.',
          effortLabel: '15 giờ • 11 blocks',
          deliverable: 'Prove Mode: Sơ đồ kiến trúc High Availability',
          sampleTasks: [
            { title: 'Thiết kế ALB + Auto Scaling Group', duration: '90m', dependency: 'Sau VPC Multi-AZ' },
            { title: 'So sánh S3 Storage Classes & Lifecycle', duration: '45m' },
          ],
          status: 'Đang thực thi (Tuần 5)',
          statusType: 'in-progress',
        },
        {
          timeframe: 'Tuần 7 - 8',
          title: 'Mock Exam & Tối Ưu Chi Phí (FinOps)',
          description: 'Giải đề thi thử theo áp lực thời gian thực và tổng hợp lỗ hổng qua Key Takeaways.',
          effortLabel: '10 giờ • 8 blocks',
          deliverable: 'Prove Mode: Đạt ≥ 82% Mock Exam',
          sampleTasks: [
            { title: 'Thi thử Full-length 65 câu SAA-C03', duration: '120m', dependency: 'Sau HA Lab' },
            { title: 'Phân tích câu sai & cập nhật Learner Memory', duration: '60m' },
          ],
          status: 'Dự kiến',
          statusType: 'upcoming',
        },
      ],
    },
    ai: {
      id: 'ai',
      tabTitle: 'Chuyển ngành AI Engineer',
      title: 'Kịch bản: Chuyển dịch năng lực AI Engineer (12 tuần)',
      objective: 'Mục tiêu: Làm chủ Hybrid RAG, Evaluation Pipeline & Production Serving',
      durationBadge: 'Thời lượng: 8h/tuần • Dự án Portfolio',
      availabilityMode: 'Mode B: T2/T4/T6 (20:00–22:00) • CN (09:00–11:00)',
      totalEffortHours: '96 giờ',
      feasibilityStatus: 'Sát ngưỡng • Khuyến nghị giữ buffer 15%',
      ragSources: ['arXiv RAG Surveys', 'pgvector & vLLM Docs'],
      milestones: [
        {
          timeframe: 'Tuần 1 - 4',
          title: 'PyTorch, Transformers & Vector DBs',
          description: 'Nắm vững Self-Attention, chunking ngữ nghĩa và indexing với pgvector.',
          effortLabel: '32 giờ • 22 blocks',
          deliverable: 'Prove Mode: Semantic Search Benchmark',
          sampleTasks: [
            { title: 'Cài đặt Embedding Pipeline & HNSW Index', duration: '90m' },
            { title: 'Đo Recall@K trên tập dữ liệu mẫu', duration: '60m', dependency: 'Sau HNSW Index' },
          ],
          status: 'Đã xong ✓',
          statusType: 'completed',
        },
        {
          timeframe: 'Tuần 5 - 8',
          title: 'Advanced RAG & AI Harness Guardrails',
          description: 'Tối ưu Hybrid Search, Re-ranking và kiểm soát prompt injection ở tầng guardrail.',
          effortLabel: '36 giờ • 24 blocks',
          deliverable: 'Prove Mode: Golden Eval 0 Regression',
          sampleTasks: [
            { title: 'Kết hợp BM25 + pgvector & Cross-Encoder', duration: '120m', dependency: 'Sau Recall@K' },
            { title: 'Viết Golden Eval offline với Mock LLM', duration: '90m', dependency: 'Sau Re-ranking' },
          ],
          status: 'Đang thực thi (Tuần 6)',
          statusType: 'in-progress',
        },
        {
          timeframe: 'Tuần 9 - 12',
          title: 'Fine-tuning Llama/Qwen & Production Serving',
          description: 'Fine-tuning LoRA/QLoRA trên dataset riêng, triển khai vLLM và đo độ trễ P95.',
          effortLabel: '28 giờ • 18 blocks',
          deliverable: 'Prove Mode: Production RAG Service',
          sampleTasks: [
            { title: 'Huấn luyện QLoRA & đánh giá Hallucination', duration: '120m', dependency: 'Sau Golden Eval' },
            { title: 'Đóng gói Streaming SSE Endpoint', duration: '90m' },
          ],
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
