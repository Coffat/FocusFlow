# Blind Review Pack — Đầu ra Milestone Planner cho 6 Mục tiêu khó (`M-01`..`M-12`)

> **Hướng dẫn đánh giá mù (Blind Review):** Tài liệu này chứa **12 phương án Milestone** cho 6 mục tiêu khó (bao gồm cả các ca cho 4 milestones lẫn ≥5 milestones), đã được xáo trộn ngẫu nhiên. Mọi thông tin về arm thử nghiệm (tool-calling vs server-prefetch), số vòng gọi tool, độ trễ và model đã được ẩn hoàn toàn.

## Bảng chấm điểm (Thang 1–5 cho mỗi tiêu chí)

- **C1 — Độ phủ mục tiêu & phạm vi:** Có bao phủ đủ các yêu cầu kỹ thuật cốt lõi trong đề bài và phù hợp deadline/quỹ giờ không?
- **C2 — Phân rã milestone & tính tiên quyết:** Số lượng milestone (kể cả ca 4 milestone) và thứ tự phụ thuộc có hợp lý, không bị gộp quá thô hoặc chẻ quá vụn không?
- **C3 — Độ sâu Learning Outcomes & Verification:** Learning outcomes và `completion_criteria` có sắc nét, đo lường được với người học mục tiêu không?
- **C4 — Cân đối Effort (`estimated_effort_minutes`):** Tổng thời lượng milestone có sát quỹ thời gian khả dụng đến `target_date` không?
- **C5 — Mức độ sẵn sàng cho bước Task Decomposer:** Nếu giao danh sách milestone này cho Decomposer rã task, cấu trúc có đủ rõ để không thiếu/lệch phạm vi không?

| Mã Plan | C1: Độ phủ mục tiêu | C2: Phân rã & Số lượng MS | C3: Outcomes & Kiểm chứng | C4: Cân đối Effort | C5: Sẵn sàng Decompose | Tổng (/25) | Ghi chú (đặc biệt các ca 4 MS) |
|---|---:|---:|---:|---:|---:|---:|---|
| **M-01** | | | | | | | |
| **M-02** | | | | | | | |
| **M-03** | | | | | | | |
| **M-04** | | | | | | | |
| **M-05** | | | | | | | |
| **M-06** | | | | | | | |
| **M-07** | | | | | | | |
| **M-08** | | | | | | | |
| **M-09** | | | | | | | |
| **M-10** | | | | | | | |
| **M-11** | | | | | | | |
| **M-12** | | | | | | | |

---

## M-01 — Kiến trúc Data Lakehouse với Apache Spark, Apache Iceberg & dbt Core

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `INTERMEDIATE`
- **Mô tả mục tiêu:** Thiết kế pipeline Medallion (Bronze-Silver-Gold) dùng PySpark Structured Streaming, Apache Iceberg ACID snapshots, hidden partitioning, compaction, xử lý data skew AQE và kiểm thử chất lượng dữ liệu với dbt trong 7 tuần.
- **Khung thời gian:** `2026-11-02` → `2026-12-21`
- **Quỹ thời gian rảnh:** MODE_B: tuesday 19:30–21:30, thursday 19:30–21:30, saturday 08:30–11:30 | Ngày nghỉ: monday, sunday
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE bao phủ toàn diện 7 tuần học (tổng 2940 phút ~ 49 giờ học thực tế với cam kết 7 giờ/tuần) theo đúng mục tiêu: từ kiến trúc metadata Apache Iceberg trên MinIO, PySpark Structured Streaming (Bronze), Hidden Partitioning & Schema Evolution & Upsert (Silver), Time-travel & Compaction, tối ưu Spark AQE & Skew Join, đến tích hợp dbt Core Data Quality Gate (Gold) và dự án tích hợp trọn vẹn End-to-End.
- **Tổng quan Milestone Plan:** 7 milestones | Tổng effort: 2940 phút (49.0 giờ)

### Danh sách Milestones

#### M1. Nền tảng Lakehouse, Môi trường Thực hành & Cấu trúc Siêu dữ liệu Apache Iceberg (420 phút | Phụ thuộc: Không)
- **Mô tả:** Dựng hạ tầng Docker Compose (Apache Spark, Apache Iceberg REST Catalog, MinIO S3 Object Storage) và giải phẫu kiến trúc siêu dữ liệu Iceberg (Metadata file, Manifest List, Manifest File).
- **Chuẩn đầu ra (Learning Outcomes):**
  - M1-O1: Khởi tạo và kết nối thành công cụm Spark với MinIO S3 và Iceberg REST Catalog qua Docker Compose.
  - M1-O2: Phân tích cấu trúc phân cấp metadata của Iceberg và cơ chế ACID transaction qua snapshot isolation.
  - M1-O3: Thực hiện tạo bảng Iceberg đầu tiên với catalog SparkSession và kiểm tra snapshot log.
- **Tiêu chí hoàn thành Milestone:** Môi trường Docker Compose hoạt động ổn định; ghi thành công dữ liệu mẫu vào bảng Iceberg trên MinIO và truy xuất đúng tệp JSON metadata cùng manifest tree sinh ra.
- **Khái niệm bổ sung (ngoài KB):** `apache-iceberg-metadata-tree`, `minio-s3-object-storage-lakehouse`, `spark-iceberg-catalog-integration`

#### M2. Thiết kế Tầng Bronze & PySpark Structured Streaming Ingestion (420 phút | Phụ thuộc: M1)
- **Mô tả:** Xây dựng luồng nhập dữ liệu streaming thời gian thực từ nguồn vào tầng Bronze dưới định dạng Iceberg, quản lý checkpointing và ngữ nghĩa exactly-once/idempotent.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M2-O1: Lập trình PySpark Structured Streaming đọc dữ liệu liên tục và ghi streaming sink vào bảng Iceberg Bronze.
  - M2-O2: Cấu hình write checkpointing và xử lý lỗi streaming failover đảm bảo tính toàn vẹn dữ liệu.
  - M2-O3: Đóng gói schema raw bất biến (append-only) cho tầng Bronze lưu giữ toàn bộ dữ liệu lịch sử thô.
- **Tiêu chí hoàn thành Milestone:** Tạo luồng Structured Streaming đẩy dữ liệu stream liên tục vào tầng Bronze của Iceberg không bị mất dữ liệu khi restart luồng và kiểm chứng qua checkpoint.
- **Khái niệm bổ sung (ngoài KB):** `pyspark-structured-streaming`, `iceberg-streaming-append-sink`, `streaming-checkpoint-idempotency`

#### M3. Tầng Silver: Hidden Partitioning, Schema Evolution & Upsert (MERGE INTO) (420 phút | Phụ thuộc: M2)
- **Mô tả:** Làm sạch, khử trùng lặp và làm giàu dữ liệu từ Bronze lên Silver, áp dụng kỹ thuật Hidden Partitioning, cập nhật cấu trúc schema không cần rewrite và thực thi MERGE INTO xử lý CDC/upsert.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M3-O1: Thiết kế bảng Silver với cơ chế Hidden Partitioning theo hàm thời gian (identity, hours, days, months) tránh rò rỉ chi tiết phân vùng vào câu lệnh SQL.
  - M3-O2: Thực hiện Schema Evolution (thêm cột, đổi kiểu an toàn, đổi tên) mà không cần sao chép hay ghi đè lại toàn bộ dữ liệu.
  - M3-O3: Viết câu lệnh MERGE INTO (upsert/delete) trong PySpark SQL để cập nhật trạng thái dữ liệu tầng Silver từ nguồn dữ liệu thay đổi (CDC).
- **Tiêu chí hoàn thành Milestone:** Thực hiện thành công truy vấn MERGE INTO trên bảng Silver có hidden partitioning, đồng thời thực thi schema evolution mà không gây lỗi phân vùng hay gián đoạn truy vấn.
- **Khái niệm bổ sung (ngoài KB):** `iceberg-hidden-partitioning`, `iceberg-schema-evolution`, `iceberg-merge-into-upsert`

#### M4. Time-Travel Query, Quản trị Snapshots & Tối ưu Small Files Compaction (420 phút | Phụ thuộc: M3)
- **Mô tả:** Nắm vững cơ chế truy vấn lịch sử (Time-Travel, Incremental Read), bảo trì bảng với Compact Data Files (Bin-pack / Sort compaction) và dọn dẹp snapshot cũ để tối ưu lưu trữ.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M4-O1: Thực thi truy vấn Time-Travel theo snapshot ID và timestamp để tái hiện trạng thái bảng trong quá khứ và rollback dữ liệu.
  - M4-O2: Cấu hình và gọi stored procedure rewrite_data_files để gộp các tệp nhỏ (compaction) do streaming sinh ra mà không chặn luồng ghi đọc concurrent.
  - M4-O3: Thiết lập quy trình expire_snapshots và remove_orphan_files để giải phóng dung lượng lưu trữ dư thừa trên MinIO.
- **Tiêu chí hoàn thành Milestone:** Chạy truy vấn time-travel thành công về snapshot trước đó; thực hiện compaction gộp nhiều file nhỏ thành file tiêu chuẩn và xóa snapshot hết hạn thành công trên bucket S3.
- **Khái niệm bổ sung (ngoài KB):** `iceberg-time-travel-history`, `iceberg-compaction-rewrite-files`, `iceberg-table-maintenance-snapshots`

#### M5. Tối ưu Hóa Hiệu năng Spark: Catalyst Optimizer, AQE & Xử lý Data Skew (420 phút | Phụ thuộc: M4)
- **Mô tả:** Đào sâu cơ chế tối ưu hóa câu truy vấn của Spark Catalyst, kích hoạt Adaptive Query Execution (AQE), xử lý mất cân bằng dữ liệu (skew join) và dynamic partition pruning.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M5-O1: Đọc và phân tích Spark Physical Plan (Logical -> Optimized -> Physical) để xác định điểm nghẽn hiệu năng I/O và shuffle.
  - M5-O2: Cấu hình và kiểm chứng tính năng Adaptive Query Execution (AQE) trong việc tự động gộp post-shuffle partitions và chuyển đổi SortMergeJoin sang BroadcastHashJoin.
  - M5-O3: Nhận diện hiện tượng Data Skew và triển khai kỹ thuật xử lý skew join (salting technique và AQE skew join handling).
- **Tiêu chí hoàn thành Milestone:** Viết kịch bản join dữ liệu bị lệch phân bố lớn (skewed dataset), so sánh Spark UI giữa trước và sau khi bật AQE/Salting, chứng minh thời gian xử lý và phân bổ task đồng đều hơn.
- **Khái niệm bổ sung (ngoài KB):** `spark-catalyst-execution-plan`, `spark-aqe-adaptive-query-execution`, `spark-data-skew-salting-optimization`

#### M6. Tầng Gold & Kiểm thử Chất lượng Dữ liệu với dbt-core trên Apache Iceberg (420 phút | Phụ thuộc: M5)
- **Mô tả:** Tích hợp dbt Core với adapter Spark/Iceberg để xây dựng mô hình dữ liệu chiều (Dimensional Modeling) tầng Gold và thiết lập bộ quy tắc Data Quality Tests.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M6-O1: Cấu hình project dbt Core kết nối với Spark Thrift Server / Iceberg Catalog.
  - M6-O2: Xây dựng các dbt model (views, incremental tables) tầng Gold phục vụ phân tích nghiệp vụ tổng hợp (Star Schema).
  - M6-O3: Định nghĩa các bài test chất lượng dữ liệu tự động (dbt generic tests, dbt-expectations) làm chốt chặn chất lượng (quality gate) cho pipeline.
- **Tiêu chí hoàn thành Milestone:** Lệnh `dbt run` chuyển đổi dữ liệu thành công lên Gold mart và toàn bộ `dbt test` kiểm tra tính duy nhất (unique), không rỗng (not_null) và ràng buộc nghiệp vụ đều vượt qua (pass).
- **Khái niệm bổ sung (ngoài KB):** `dbt-core-spark-iceberg-setup`, `dbt-dimensional-modeling-gold`, `dbt-data-quality-testing`

#### M7. Dự án Tốt nghiệp: Pipeline Medallion Lakehouse Tích hợp End-to-End (420 phút | Phụ thuộc: M6)
- **Mô tả:** Tích hợp toàn bộ hệ thống Medallion hoàn chỉnh: Streaming Ingestion -> Iceberg Bronze -> Silver Upsert/Cleaning -> Gold Mart qua dbt, tối ưu AQE và bảo trì compaction tự động.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M7-O1: Triển khai pipeline khép kín từ ingestion dữ liệu stream đến tầng Gold phân tích theo chuẩn kiến trúc Medallion.
  - M7-O2: Tích hợp kịch bản kiểm thử data quality gate tự động và cơ chế khôi phục dữ liệu bằng time-travel khi phát hiện dữ liệu lỗi.
  - M7-O3: Đóng gói tài liệu kiến trúc, đo kiểm hiệu năng pipeline và quy trình vận hành bảo trì (compaction, snapshot expiration).
- **Tiêu chí hoàn thành Milestone:** Toàn bộ pipeline chạy trơn tru qua script điều phối tự động: stream dữ liệu vào Bronze, xử lý sang Silver với MERGE INTO, tạo Gold mart qua dbt tests đạt 100%, kèm báo cáo benchmark hiệu năng và runbook bảo trì Iceberg.
- **Khái niệm bổ sung (ngoài KB):** `end-to-end-medallion-lakehouse-architecture`, `production-lakehouse-runbook-governance`

---

## M-02 — Hệ thống MLOps & LLMOps Production: vLLM Serving, Eval Harness & Drift Monitoring

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `ADVANCED`
- **Mô tả mục tiêu:** Triển khai pipeline serving LLM/ML chuẩn production với vLLM continuous batching, Prompt & Model Registry, Eval Harness tự động (pass@1, faithfulness, latency p95), guardrails chống prompt injection và Prometheus/Grafana drift alerting trong 8 tuần.
- **Khung thời gian:** `2026-11-02` → `2026-12-28`
- **Quỹ thời gian rảnh:** MODE_B: monday 20:00–22:00, thursday 20:00–22:00, sunday 09:00–12:00 | Ngày nghỉ: wednesday, saturday
- **Tóm tắt phạm vi lộ trình:** Lộ trình Full Scope kéo dài 8 tuần với tổng cộng 3000 phút (~50 giờ nỗ lực), phân bổ đều đặn theo quỹ thời gian 7 giờ/tuần. Lộ trình bao phủ toàn diện từ kiến trúc vLLM serving, benchmark tải và tail latency p95, xây dựng LLM Gateway có Prompt Registry và Guardrails, pipeline CI Eval Harness tự động chặn hồi quy, đến hệ thống giám sát Prometheus/Grafana drift alerting và diễn tập chaos testing chuẩn Staff MLOps.
- **Tổng quan Milestone Plan:** 6 milestones | Tổng effort: 3000 phút (50.0 giờ)

### Danh sách Milestones

#### M1. Kiến trúc vLLM Serving, PagedAttention và Tối ưu KV-Cache (420 phút | Phụ thuộc: Không)
- **Mô tả:** Nắm vững nguyên lý PagedAttention, Continuous Batching, cấu hình GPU memory utilization và triển khai vLLM serving container chuẩn production cho open-weights LLM.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M1-O1: Phân tích cơ chế bộ nhớ PagedAttention và Continuous Batching so sánh với static batching truyền thống.
  - M1-O2: Đóng gói và cấu hình vLLM OpenAI-compatible server với tensor parallelism và tham số KV-cache tối ưu trên GPU cloud.
- **Tiêu chí hoàn thành Milestone:** Container vLLM chạy ổn định trên GPU cloud, phục vụ model (ví dụ Llama/Mistral) qua OpenAI-compatible API với latency baseline được ghi nhận dưới tải cơ bản.
- **Khái niệm bổ sung (ngoài KB):** `vllm-serving-architecture`, `paged-attention-kv-cache`, `continuous-batching-engine`

#### M2. High-Throughput Benchmarking & Tail Latency (p95/p99) Profiling (480 phút | Phụ thuộc: M1)
- **Mô tả:** Xây dựng pipeline benchmark tải đồng thời, đo lường throughput (tokens/sec), time-to-first-token (TTFT), time-per-output-token (TPOT) và phân tích tail latency.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M2-O1: Thiết kế kịch bản stress-test mô phỏng traffic production bằng công cụ benchmark (Locust/vLLM benchmark suite).
  - M2-O2: Phân tích và tinh chỉnh các tham số max-num-seqs, max-model-len để tối ưu tail latency p95/p99 và ngăn ngừa out-of-memory (OOM).
- **Tiêu chí hoàn thành Milestone:** Báo cáo benchmark so sánh throughput và latency curves đạt mục tiêu SLA, kiểm soát tail latency p95 dưới 1.5s trong điều kiện tải đồng thời 50 concurrent requests.
- **Khái niệm bổ sung (ngoài KB):** `llm-latency-profiling-ttft-tpot`, `gpu-concurrency-benchmarking`

#### M3. LLM Gateway, Prompt Registry Checksum & Guardrails Chống Prompt Injection (540 phút | Phụ thuộc: M1)
- **Mô tả:** Xây dựng tầng API Gateway trung gian với quản lý phiên bản Prompt Registry có checksum, tích hợp bộ lọc Guardrails phát hiện Prompt Injection và rò rỉ dữ liệu.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M3-O1: Tích hợp hệ thống quản lý Prompt Registry kiểm soát versioning qua Git commit hash/checksum và template hydration an toàn.
  - M3-O2: Thiết lập pipeline Guardrails kết hợp rule-based regex và classifier/heuristics nhằm chặn jailbreak và prompt injection trước khi gửi tới engine vLLM.
- **Tiêu chí hoàn thành Milestone:** Hệ thống Gateway từ chối 100% các test vector prompt injection cơ bản và duy trì khả năng truy vết prompt version tương ứng qua request metadata.
- **Khái niệm đã xác minh (KB):** `ai-llm-structured-rag-agents`
- **Khái niệm bổ sung (ngoài KB):** `prompt-registry-checksum-versioning`, `llm-guardrails-prompt-injection`

#### M4. Automated Eval Harness & CI Regression Quality Gate (600 phút | Phụ thuộc: M3)
- **Mô tả:** Tích hợp framework đánh giá tự động (Eval Harness) đo lường pass@1, faithfulness, answer relevancy và thiết lập CI regression gate chặn suy giảm chất lượng model.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M4-O1: Xây dựng bộ test dataset chuẩn hóa và thực thi đánh giá tự động với các metric pass@1, faithfulness và semantic similarity.
  - M4-O2: Tích hợp Eval Gate vào pipeline CI/CD (GitHub Actions) để tự động kích hoạt evaluation run và chặn merge/deploy nếu metric thụt lùi quá ngưỡng cho phép.
- **Tiêu chí hoàn thành Milestone:** Pipeline CI chạy tự động qua Eval Harness, xuất báo cáo regression so sánh model/prompt checkpoint và tự động fail job nếu pass@1 hoặc faithfulness giảm quá 5%.
- **Khái niệm đã xác minh (KB):** `ai-llm-structured-rag-agents`
- **Khái niệm bổ sung (ngoài KB):** `automated-eval-harness`, `ci-cd-llm-regression-gate`, `ragas-faithfulness-evaluation`

#### M5. Prometheus Metrics, Statistical Drift Monitoring & Production Alerting (540 phút | Phụ thuộc: M2, M4)
- **Mô tả:** Xuất metric từ vLLM và Gateway sang Prometheus, trực quan hóa qua Grafana dashboard và thiết lập hệ thống cảnh báo Data/Concept Drift và SLA vi phạm.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M5-O1: Thu thập và chuẩn hóa telemetry metrics từ vLLM (cache hit rate, queue time, token count) và Gateway qua Prometheus exporter.
  - M5-O2: Xây dựng cơ chế phát hiện statistical drift trên phân phối chiều dài prompt, embedding drift và cấu hình Grafana Alert rules (slack/webhook) khi p95 latency hoặc drift vượt ngưỡng.
- **Tiêu chí hoàn thành Milestone:** Grafana dashboard hoàn chỉnh hiển thị live throughput, queue length, token consumption và kích hoạt thành công cảnh báo giả lập vi phạm tail latency p95 / drift anomaly.
- **Khái niệm bổ sung (ngoài KB):** `prometheus-vllm-telemetry`, `grafana-llmops-monitoring`, `statistical-data-drift-detection`

#### M6. Tích hợp E2E Production Stack, Chaos Testing & Audit Sẵn sàng Triển khai (420 phút | Phụ thuộc: M5)
- **Mô tả:** Kiểm thử tải toàn diện End-to-End, mô phỏng lỗi GPU/vLLM crash (chaos testing), tinh chỉnh giới hạn tài nguyên và nghiệm thu toàn bộ hệ thống chuẩn Staff MLOps.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M6-O1: Thực hiện kịch bản chaos testing (kill vLLM process, nghẽn mạng Redis/DB) để kiểm tra tính năng tự phục hồi và graceful degradation của Gateway.
  - M6-O2: Hoàn thiện tài liệu kiến trúc, runbook vận hành xử lý sự cố p95 degradation và checklist go-live cho cụm production LLM serving.
- **Tiêu chí hoàn thành Milestone:** Hệ thống vượt qua bài kiểm tra chịu tải liên tục 30 phút dưới áp lực chaos testing mà không làm mất mát request quan trọng, có đầy đủ runbook và dashboard chứng minh SLA.
- **Khái niệm bổ sung (ngoài KB):** `e2e-llmops-chaos-engineering`, `production-sla-readiness-audit`

---

## M-03 — Bảo mật Kubernetes Production & Hạ tầng Terraform Multi-Account (Zero-Trust)

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `ADVANCED`
- **Mô tả mục tiêu:** Xây dựng hạ tầng EKS/GKE bằng Terraform Modules (remote state locking, OIDC), áp dụng Pod Security Standards, NetworkPolicy Calico/Cilium, Kyverno Policy-as-Code, Falco runtime detection và Supply Chain SBOM/Cosign trong 4 tuần.
- **Khung thời gian:** `2026-11-02` → `2026-11-30`
- **Quỹ thời gian rảnh:** MODE_B: monday 19:30–21:30, wednesday 19:30–21:30, thursday 19:30–21:30, sunday 09:00–12:00 | Ngày nghỉ: tuesday, saturday
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE chuẩn hóa 4 tuần (36 giờ học thực hành chuyên sâu) bao phủ toàn diện mục tiêu: Từ cấu hình hạ tầng Terraform Multi-Account với OIDC/IRSA, thiết lập mạng Zero-Trust với Cilium/Calico, áp dụng Policy-as-Code và PSS với Kyverno, đến bảo vệ chuỗi cung ứng bằng Cosign/SBOM và phát hiện tấn công runtime bằng Falco, đảm bảo cụm sẵn sàng đạt chuẩn CIS Benchmark.
- **Tổng quan Milestone Plan:** 4 milestones | Tổng effort: 2160 phút (36.0 giờ)

### Danh sách Milestones

#### M1. Hạ tầng Terraform Multi-Account & Bảo mật Quản trị Danh tính (OIDC/IRSA) (540 phút | Phụ thuộc: Không)
- **Mô tả:** Xây dựng hạ tầng cụm EKS/GKE theo kiến trúc module đa tài khoản, quản lý remote state an toàn với S3/DynamoDB locking, cấu hình OIDC provider kết nối IAM Roles for Service Accounts (IRSA) và quét mã nguồn IaC với tfsec/checkov.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M1-O1: Thiết kế và triển khai Terraform Module cụm Kubernetes hỗ trợ remote backend S3 mã hóa KMS và state locking DynamoDB.
  - M1-O2: Cấu hình OIDC Identity Provider liên kết IAM Role với Kubernetes ServiceAccount (IRSA) tuân thủ nguyên tắc đặc quyền tối thiểu (Least Privilege).
  - M1-O3: Tích hợp tfsec và checkov vào quy trình kiểm thử IaC nhằm phát hiện và khắc phục các cấu hình sai lệch bảo mật hạ tầng.
- **Tiêu chí hoàn thành Milestone:** Mã nguồn Terraform triển khai thành công cụm Kubernetes với OIDC xác thực IAM hợp lệ, vượt qua 100% các quy tắc kiểm tra bảo mật tĩnh của tfsec và checkov không có lỗi High/Critical.
- **Khái niệm bổ sung (ngoài KB):** `Terraform Remote State & State Locking`, `Terraform Multi-Account Architecture`, `Kubernetes OIDC & AWS IRSA`, `IaC Security Scanning (tfsec & checkov)`

#### M2. Mạng Zero-Trust & Phân vùng Truy cập với Cilium/Calico NetworkPolicy (540 phút | Phụ thuộc: M1)
- **Mô tả:** Triển khai CNI nâng cao (Cilium eBPF hoặc Calico), thiết lập chính sách Default-Deny, phân tách cô lập lưu lượng pod-to-pod, kiểm soát egress/ingress tại tầng Layer 3/4 và Layer 7.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M2-O1: Cài đặt và cấu hình CNI Cilium (eBPF) trên cụm thực hành (kind/k3s/cloud) để giám sát và thực thi chính sách mạng.
  - M2-O2: Soạn thảo và áp dụng mô hình Zero-Trust với NetworkPolicy/CiliumNetworkPolicy chế độ Default-Deny cho cả ingress và egress.
  - M2-O3: Kiểm soát lưu lượng L7 (HTTP/DNS inspection) và giới hạn truy cập ra bên ngoài chỉ cho phép các FQDN được phê duyệt.
- **Tiêu chí hoàn thành Milestone:** Tất cả namespace áp dụng chính sách Default-Deny; pod thử nghiệm chỉ giao tiếp được đúng endpoint được chỉ định qua NetworkPolicy và chặn hoàn toàn các nỗ lực quét cổng trái phép trong cụm.
- **Khái niệm bổ sung (ngoài KB):** `Cilium eBPF & Calico CNI`, `Kubernetes NetworkPolicy Zero-Trust`, `L7 Traffic Filtering & DNS Egress Inspection`

#### M3. Admission Control, Hardening Pod Security & Policy-as-Code với Kyverno (540 phút | Phụ thuộc: M2)
- **Mô tả:** Áp dụng Pod Security Standards (PSS) cấp độ Restricted, thiết lập Kyverno admission controller để chặn container chạy quyền root, ngăn ngừa leo thang đặc quyền (privilege escalation) và enforces compliance tự động.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M3-O1: Cấu hình namespace áp dụng Pod Security Admission (PSA) ở mức 'restricted' và xác thực cơ chế chặn pod vi phạm.
  - M3-O2: Viết các chính sách Kyverno ClusterPolicy chặn root user, cấm privileged containers, bắt buộc read-only root filesystem và cấu hình resource limits.
  - M3-O3: Thực hiện mô phỏng tấn công leo thang đặc quyền container breakout và kiểm chứng năng lực ngăn chặn của Kyverno.
- **Tiêu chí hoàn thành Milestone:** Mọi manifest vi phạm PSS Restricted hoặc thiếu nhãn bảo mật bắt buộc đều bị Kyverno webhook từ chối (Deny admission); kịch bản tấn công khai thác quyền root cục bộ bị vô hiệu hóa.
- **Khái niệm bổ sung (ngoài KB):** `Kubernetes Pod Security Standards (PSS/PSA)`, `Kyverno Policy-as-Code`, `Container Privilege Escalation Mitigation`

#### M4. Supply Chain Security (Cosign/SBOM) & Phát hiện Bất thường Runtime với Falco (540 phút | Phụ thuộc: M3)
- **Mô tả:** Bảo vệ chuỗi cung ứng phần mềm bằng việc ký và xác thực container image với Sigstore Cosign, tạo và quét SBOM (Syft/Grype), kết hợp cài đặt Falco phát hiện các hành vi bất thường và syscall đáng ngờ tại runtime.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M4-O1: Tạo khóa, ký container image và sinh SBOM (Software Bill of Materials) trong pipeline CI/CD GitHub Actions.
  - M4-O2: Tích hợp xác thực chữ ký số image bằng Kyverno/Cosign admission rule, chỉ cho phép image đã ký được triển khai vào cụm.
  - M4-O3: Triển khai Falco trên cụm, tùy biến các quy tắc cảnh báo hành vi xâm nhập runtime (đọc file nhạy cảm, mở reverse shell, ghi đè file binary).
- **Tiêu chí hoàn thành Milestone:** Pipeline tự động ký image và đẩy SBOM; cụm từ chối chạy image không có chữ ký hợp lệ; Falco phát hiện và bắn cảnh báo ngay lập tức khi thực thi lệnh mở shell bất thường trong container.
- **Khái niệm bổ sung (ngoài KB):** `Supply Chain Security (Sigstore Cosign & SBOM)`, `Container Image Vulnerability Scanning`, `Falco Runtime Threat Detection & Syscall Monitoring`, `Kubernetes CIS Benchmark Hardening`

---

## M-04 — Bảo mật Kubernetes Production & Hạ tầng Terraform Multi-Account (Zero-Trust)

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `ADVANCED`
- **Mô tả mục tiêu:** Xây dựng hạ tầng EKS/GKE bằng Terraform Modules (remote state locking, OIDC), áp dụng Pod Security Standards, NetworkPolicy Calico/Cilium, Kyverno Policy-as-Code, Falco runtime detection và Supply Chain SBOM/Cosign trong 4 tuần.
- **Khung thời gian:** `2026-11-02` → `2026-11-30`
- **Quỹ thời gian rảnh:** MODE_B: monday 19:30–21:30, wednesday 19:30–21:30, thursday 19:30–21:30, sunday 09:00–12:00 | Ngày nghỉ: tuesday, saturday
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE thiết kế trong 4 tuần (tương ứng 36 giờ nỗ lực theo thời gian biểu 9 giờ/tuần) bao phủ toàn diện mục tiêu: từ hạ tầng IaC Terraform bảo mật đa tài khoản với OIDC/IRSA, mạng zero-trust Cilium eBPF, Admission Control với Kyverno & Pod Security Standards, đến chuỗi cung ứng container (Cosign/SBOM) và giám sát runtime syscall với Falco.
- **Tổng quan Milestone Plan:** 4 milestones | Tổng effort: 2160 phút (36.0 giờ)

### Danh sách Milestones

#### M1. Thiết kế Hạ tầng Terraform Multi-Account & EKS Hardened với OIDC (540 phút | Phụ thuộc: Không)
- **Mô tả:** Xây dựng hạ tầng cụm EKS/GKE chuẩn Enterprise bằng Terraform Modules có remote state locking (S3/DynamoDB), tích hợp IRSA (IAM Roles for Service Accounts) qua OIDC Provider, áp dụng công cụ quét tĩnh tfsec/checkov và thiết lập RBAC ít đặc quyền.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M1-O1: Thiết kế và module hóa Terraform cho kiến trúc đa tài khoản với remote state locking và encryption-at-rest.
  - M1-O2: Tích hợp AWS IAM Roles for Service Accounts (IRSA) thông qua EKS OIDC identity provider.
  - M1-O3: Cấu hình RBAC trên Kubernetes theo nguyên tắc least privilege và kiểm tra static analysis bằng tfsec/checkov.
- **Tiêu chí hoàn thành Milestone:** Mã Terraform vượt qua kiểm tra static analysis (0 lỗi high/critical từ checkov/tfsec), cụm EKS tạo thành công với OIDC identity mapping và Pod kiểm thử có thể giả lập IAM Role thông qua Web Identity Token mà không dùng hardcoded secrets.
- **Khái niệm bổ sung (ngoài KB):** `terraform-multi-account-modules`, `eks-oidc-irsa-least-privilege`, `iac-security-scanning-checkov-tfsec`

#### M2. Mạng Zero-Trust & NetworkPolicy Chuyên sâu với Cilium eBPF (540 phút | Phụ thuộc: M1)
- **Mô tả:** Triển khai giải pháp CNI Cilium trên Kubernetes để thực thi mô hình Zero-Trust Network. Viết và kiểm thử các chính sách CiliumNetworkPolicy (L3/L4/L7), cách ly namespace, lọc egress theo FQDN và giám sát lưu lượng qua Hubble.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M2-O1: Cài đặt và cấu hình Cilium CNI sử dụng eBPF datapath thay thế kube-proxy.
  - M2-O2: Soạn thảo và áp dụng CiliumNetworkPolicy ở tầng L3/L4 và L7 (HTTP method/path filtering).
  - M2-O3: Phân tích và truy vết lưu lượng mạng bị chặn hoặc cho phép thông qua Hubble UI/CLI.
- **Tiêu chí hoàn thành Milestone:** Cụm Kubernetes kích hoạt thành công Cilium eBPF; triển khai 2 service microservices và xác nhận traffic trái phép bị chặn ở mức L7 (HTTP), chỉ cho phép egress đến domain chỉ định qua FQDN policy và ghi nhận log rõ ràng trên Hubble.
- **Khái niệm bổ sung (ngoài KB):** `cilium-ebpf-zero-trust-cni`, `l3-l4-l7-network-policies`, `hubble-network-observability`

#### M3. Kiểm soát Admission Control, Pod Security Standards & Kyverno Policy-as-Code (540 phút | Phụ thuộc: M1, M2)
- **Mô tả:** Thiết lập cơ chế Policy-as-Code sử dụng Kyverno Admission Controller, áp dụng chuẩn Pod Security Standards (Restricted profile), ngăn chặn leo thang đặc quyền (privilege escalation), loại bỏ root container và thực hành tấn công giả lập rồi khắc phục.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M3-O1: Cấu hình Kubernetes Pod Security Standards ở mức Restricted cho các namespace ứng dụng.
  - M3-O2: Xây dựng các quy tắc Kyverno Validate, Mutate và Generate để bắt buộc Pod có SecurityContext an toàn.
  - M3-O3: Thực hiện kịch bản tấn công giả lập (hostPath mount, cap-add SYS_ADMIN) và xác thực chính sách Kyverno chặn đứng thành công.
- **Tiêu chí hoàn thành Milestone:** Kyverno chặn 100% các yêu cầu tạo Pod vi phạm (như chạy dưới quyền root, privileged: true, hoặc gắn hostPath nhạy cảm) trong kịch bản kiểm thử tấn công, đồng thời audit report đạt chuẩn CIS Kubernetes Benchmark đối với Pod Security.
- **Khái niệm bổ sung (ngoài KB):** `pod-security-standards-restricted`, `kyverno-policy-as-code`, `privilege-escalation-mitigation-k8s`

#### M4. Bảo mật Chuỗi cung ứng (SBOM/Cosign) & Giám sát Runtime Syscall với Falco (540 phút | Phụ thuộc: M3)
- **Mô tả:** Hoàn thiện hệ sinh thái phòng thủ toàn diện: tích hợp ký ảnh số và xác thực chữ ký container qua Sigstore Cosign/Kyverno, sinh SBOM với Syft/Trivy trong CI/CD, và triển khai Falco để phát hiện bất thường runtime dựa trên Linux syscall.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M4-O1: Tạo khóa, ký container image với Cosign và cấu hình Kyverno verifyImage để từ chối image chưa ký.
  - M4-O2: Tạo và kiểm định Software Bill of Materials (SBOM) bằng Syft và quét lỗ hổng phụ thuộc trong CI/CD.
  - M4-O3: Triển khai Falco DaemonSet với custom rules để phát hiện các hành vi khả nghi (spawn shell trong pod, đọc /etc/shadow) tại runtime.
- **Tiêu chí hoàn thành Milestone:** Admission webhook từ chối các container image chưa có chữ ký Cosign hợp lệ; đồng thời khi thực thi hành vi tương tác bash shell hoặc đọc file hệ thống trái phép bên trong Pod, Falco phát hiện và đẩy alert thời gian thực.
- **Khái niệm bổ sung (ngoài KB):** `sigstore-cosign-image-signing`, `sbom-generation-vulnerability-scanning`, `falco-runtime-syscall-detection`

---

## M-05 — Hệ thống Phân tán hiệu năng cao với Go: Raft Consensus, gRPC & Distributed Tracing

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `ADVANCED`
- **Mô tả mục tiêu:** Thiết kế và cài đặt cụm lưu trữ Key-Value chịu lỗi dùng Go, Raft leader election & log replication, gRPC streaming, circuit breaker và OpenTelemetry distributed tracing trong 4 tuần. Cần xử lý race condition với Goroutines/Channels và benchmark p99 latency.
- **Khung thời gian:** `2026-11-02` → `2026-11-30`
- **Quỹ thời gian rảnh:** MODE_B: monday 19:30–21:30, tuesday 19:30–21:30, thursday 19:30–21:30, saturday 09:00–12:00 | Ngày nghỉ: wednesday, sunday
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE trong 4 tuần (tổng nỗ lực 36 giờ, 9h/tuần) bao phủ toàn bộ mục tiêu: xây dựng cụm Key-Value 3-node chịu lỗi bằng Go sử dụng thuật toán đồng thuận Raft (Leader Election, Log Replication, Snapshotting), tầng giao tiếp gRPC streaming, Circuit Breaker, giám sát OpenTelemetry Tracing và kiểm thử Chaos chịu lỗi phân tán.
- **Tổng quan Milestone Plan:** 4 milestones | Tổng effort: 2160 phút (36.0 giờ)

### Danh sách Milestones

#### M1. Cơ chế Đồng thuận Raft: Leader Election & Log Replication (540 phút | Phụ thuộc: Không)
- **Mô tả:** Nghiên cứu đặc tả Raft paper và cài đặt state machine cốt lõi bằng Go thuần: State transitions (Follower, Candidate, Leader), cơ chế Heartbeat, RequestVote, AppendEntries RPC logic, và xử lý an toàn luồng với Goroutines, Channels, Mutex chống race condition.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M1-O1: Cài đặt cỗ máy trạng thái Raft Node (Follower, Candidate, Leader) với randomized election timeout và RequestVote RPC logic
  - M1-O2: Xử lý cơ chế AppendEntries RPC, kiểm tra log matching property và commit index tiến dần khi đạt đa số (quorum)
  - M1-O3: Đảm bảo đồng bộ luồng nội bộ không bị deadlock hay race condition thông qua go test -race
- **Tiêu chí hoàn thành Milestone:** Vượt qua toàn bộ bộ unit test cho Leader Election và Log Replication với cờ '-race' chạy thành công; mô phỏng election khi rớt mạng leader cũ và node mới nhận đa số phiếu trong vòng 300ms.
- **Khái niệm bổ sung (ngoài KB):** `raft-consensus-algorithm`, `go-concurrency-patterns`, `raft-leader-election`, `raft-log-replication`

#### M2. Giao tiếp gRPC Streaming & Tầng Service KV Store (540 phút | Phụ thuộc: M1)
- **Mô tả:** Định nghĩa Protobuf schemas cho dịch vụ KV Store và nội bộ Raft peer RPC. Cài đặt gRPC Server/Client với Bi-directional streaming, gRPC Interceptors cho logging/metadata, và tích hợp Circuit Breaker bảo vệ node khi rớt mạng.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M2-O1: Thiết kế Protocol Buffers schema (v3) cho cả client-facing KV operations (Get, Put, Delete) và internal peer Raft communication
  - M2-O2: Cài đặt gRPC streaming và Custom Interceptors hỗ trợ timeout propagation, context cancellation và phân luồng request
  - M2-O3: Tích hợp cơ chế Circuit Breaker và Retry có Jitter Exponential Backoff cho các cuộc gọi giữa các node trong cụm
- **Tiêu chí hoàn thành Milestone:** Node Raft giao tiếp thông suốt qua gRPC client/server; xử lý thành công Put/Get stream request từ client và tự động ngắt kết nối tạm thời (open circuit) khi node đích unreachable.
- **Khái niệm bổ sung (ngoài KB):** `grpc-protobuf-go`, `grpc-interceptors-streaming`, `distributed-circuit-breaker`

#### M3. State Machine Replication, Log Compaction & Snapshot (540 phút | Phụ thuộc: M1, M2)
- **Mô tả:** Hoàn thiện tầng Finite State Machine (FSM) cho Key-Value store áp dụng log entries. Cài đặt cơ chế Snapshotting và Log Compaction để giải phóng bộ nhớ, kèm InstallSnapshot RPC khi một follower bị tụt log quá xa.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M3-O1: Ánh xạ committed Raft log entries vào in-memory KV state machine đảm bảo tính nhất quán tuần tự (linearizability)
  - M3-O2: Cài đặt thuật toán Snapshot Compaction ghi trạng thái hiện tại ra disk và cắt tỉa (truncate) log cũ
  - M3-O3: Triển khai InstallSnapshot RPC để catch-up nhanh chóng các node tụt hậu xa mà không gửi toàn bộ chuỗi log lịch sử
- **Tiêu chí hoàn thành Milestone:** Chạy benchmark ghi 50,000 keys; kích hoạt trigger snapshot tự động, nén log thành công và một follower khởi động lại có thể đồng bộ tức thì bằng snapshot.
- **Khái niệm bổ sung (ngoài KB):** `raft-log-compaction-snapshotting`, `finite-state-machine-replication`, `linearizable-kv-storage`

#### M4. OpenTelemetry Tracing, Chaos Testing & Tối ưu P99 Latency Cụm 3-Node (540 phút | Phụ thuộc: M2, M3)
- **Mô tả:** Đóng gói cụm 3-node trên Docker Compose. Tích hợp OpenTelemetry Go SDK xuất trace/spans sang Jaeger/Zipkin. Viết kịch bản Chaos fault-injection kiểm thử Network Partition (Split-brain recovery) và đo lường tối ưu p99 latency.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M4-O1: Tích hợp OpenTelemetry Go SDK với context trace propagation qua gRPC metadata cho phép theo dõi end-to-end từ client đến leader và followers
  - M4-O2: Tạo môi trường Docker Compose 3-node và viết kịch bản Chaos Test (Network Partition / kill leader) kiểm chứng tính chịu lỗi và tránh split-brain
  - M4-O3: Đo lường và tối ưu hóa p99 latency dưới tải đồng thời (concurrency benchmark) bằng pprof profiling và buffer pooling
- **Tiêu chí hoàn thành Milestone:** Cụm 3-node Docker vượt qua kịch bản cô lập 1 node (partition) mà vẫn phục vụ ghi từ quorum; OpenTelemetry exporter hiển thị đầy đủ distributed trace flamegraph; p99 latency đo được dưới tải ổn định theo SLA thiết kế.
- **Khái niệm bổ sung (ngoài KB):** `opentelemetry-distributed-tracing`, `chaos-testing-network-partition`, `p99-latency-profiling-pprof`, `docker-distributed-cluster`

---

## M-06 — Kiến trúc Data Lakehouse với Apache Spark, Apache Iceberg & dbt Core

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `INTERMEDIATE`
- **Mô tả mục tiêu:** Thiết kế pipeline Medallion (Bronze-Silver-Gold) dùng PySpark Structured Streaming, Apache Iceberg ACID snapshots, hidden partitioning, compaction, xử lý data skew AQE và kiểm thử chất lượng dữ liệu với dbt trong 7 tuần.
- **Khung thời gian:** `2026-11-02` → `2026-12-21`
- **Quỹ thời gian rảnh:** MODE_B: tuesday 19:30–21:30, thursday 19:30–21:30, saturday 08:30–11:30 | Ngày nghỉ: monday, sunday
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE trải dài 7 tuần (tương ứng 7 cột mốc, 420 phút/tuần = 7 giờ/tuần theo cam kết của học viên), bao phủ trọn vẹn kiến trúc Medallion Lakehouse với Apache Spark, Apache Iceberg trên MinIO S3, kỹ thuật Structured Streaming, Schema Evolution, AQE Skew Join, Compaction và Data Quality Gate với dbt Core.
- **Tổng quan Milestone Plan:** 7 milestones | Tổng effort: 2940 phút (49.0 giờ)

### Danh sách Milestones

#### M1. Thiết lập nền tảng Lakehouse với Docker Compose, MinIO S3 & Apache Iceberg REST Catalog (420 phút | Phụ thuộc: Không)
- **Mô tả:** Xây dựng môi trường giả lập Object Storage tương thích S3 bằng MinIO, cấu hình Apache Iceberg REST Catalog và kết nối Apache Spark qua PySpark để thực hiện các thao tác DDL/DML đầu tiên.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M1-O1: Khởi tạo và liên kết thành công môi trường multi-container gồm MinIO S3, Iceberg REST Catalog và Spark Thrift/Jupyter
  - M1-O2: Cấu hình SparkSession tích hợp Iceberg SparkCatalog, S3FileIO và xác thực MinIO endpoint
  - M1-O3: Thực thi tạo bảng Iceberg (CREATE TABLE), nạp dữ liệu mẫu và quan sát cấu trúc thư mục metadata trên MinIO
- **Tiêu chí hoàn thành Milestone:** Môi trường Docker Compose hoạt động ổn định; PySpark script tạo thành công database và bảng Iceberg trên MinIO bucket, đọc ghi được 1000 bản ghi mẫu không lỗi.
- **Khái niệm bổ sung (ngoài KB):** `apache-iceberg-rest-catalog`, `minio-s3-fileio-integration`, `pyspark-iceberg-configuration`

#### M2. Kiến trúc Metadata Iceberg, Hidden Partitioning & ACID Snapshots (420 phút | Phụ thuộc: M1)
- **Mô tả:** Nghiên cứu sâu cơ chế metadata 3 tầng của Iceberg (Metadata file, Manifest list, Manifest file), kỹ thuật hidden partitioning, snapshot isolation và tính năng Time Travel / Rollback.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M2-O1: Phân tích cây metadata manifest và snapshot tree để giải thích tính năng ACID transaction trên Object Storage
  - M2-O2: Thiết kế bảng với Hidden Partitioning (identity, hours, days, bucket, truncate) và chứng minh partition pruning không cần filter thủ công
  - M2-O3: Thực hiện truy vấn Time Travel (theo snapshot_id và timestamp-as-of) và rollback dữ liệu về trạng thái trước đó
- **Tiêu chí hoàn thành Milestone:** Giải trình chính xác nội dung file metadata json/avro và viết truy vấn Spark SQL chứng minh partition pruning và time-travel thành công trên tập dữ liệu kiểm thử.
- **Khái niệm bổ sung (ngoài KB):** `iceberg-metadata-manifest-tree`, `iceberg-hidden-partitioning`, `iceberg-acid-snapshots-time-travel`

#### M3. PySpark Structured Streaming & Medallion Bronze Ingestion (420 phút | Phụ thuộc: M2)
- **Mô tả:** Xây dựng tầng Bronze để ingest dữ liệu streaming theo thời gian thực hoặc micro-batch từ nguồn streaming giả lập vào Apache Iceberg sử dụng PySpark Structured Streaming với checkpointing an toàn.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M3-O1: Xây dựng pipeline PySpark Structured Streaming đọc dữ liệu streaming và ghi vào tầng Bronze định dạng Iceberg
  - M3-O2: Cấu hình Checkpointing và Write-Ahead Log (WAL) trên MinIO đảm bảo ngữ nghĩa Exactly-Once / At-Least-Once
  - M3-O3: Xử lý dữ liệu thô với schema linh hoạt và theo dõi StreamingQueryProgressMonitor
- **Tiêu chí hoàn thành Milestone:** Pipeline streaming Bronze hoạt động liên tục, tự phục hồi sau khi restart từ checkpoint mà không làm thất thoát hoặc nhân đôi dữ liệu.
- **Khái niệm bổ sung (ngoài KB):** `pyspark-structured-streaming-iceberg`, `lakehouse-medallion-bronze-architecture`, `streaming-checkpointing-fault-tolerance`

#### M4. Tầng Silver: Streaming Upsert với MERGE INTO & Schema Evolution Không Downtime (420 phút | Phụ thuộc: M3)
- **Mô tả:** Làm sạch, khử trùng lặp và cập nhật dữ liệu thay đổi (CDC/Upsert) từ Bronze sang Silver thông qua cú pháp MERGE INTO, đồng thời áp dụng Schema Evolution an toàn.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M4-O1: Hiện thực hóa cú pháp MERGE INTO trong Spark SQL/PySpark để xử lý CDC upsert/delete vào bảng Iceberg Silver
  - M4-O2: Áp dụng các thay đổi cấu trúc bảng (add column, rename, reorder, drop column) mà không cần rewrite toàn bộ dữ liệu
  - M4-O3: Xây dựng cơ chế Dead Letter Queue (DLQ) cách ly các bản ghi sai định dạng ở tầng Silver
- **Tiêu chí hoàn thành Milestone:** Thực hiện thành công batch upsert 50.000 bản ghi CDC có chứa cả UPDATE/INSERT và chứng minh bảng vẫn truy vấn bình thường sau khi rename/add cột mới.
- **Khái niệm bổ sung (ngoài KB):** `iceberg-merge-into-cdc-upsert`, `iceberg-in-place-schema-evolution`, `lakehouse-medallion-silver-cleansing`

#### M5. Tối ưu hóa Hiệu năng: Adaptive Query Execution (AQE), Skew Join & Compaction (420 phút | Phụ thuộc: M4)
- **Mô tả:** Nắm vững cơ chế Catalyst Optimizer, kích hoạt AQE để xử lý Data Skew, điều chỉnh partition tự động và thiết lập chu trình bảo trì bảng (Compaction, Expire Snapshots, Orphan Files cleanup).
- **Chuẩn đầu ra (Learning Outcomes):**
  - M5-O1: Kích hoạt và cấu hình Spark Adaptive Query Execution (AQE) để tự động xử lý skew join và dynamic partition coalescing
  - M5-O2: Chẩn đoán Spark UI (DAG, metrics, spill to disk) để nhận diện các nút thắt cổ chai và data skew
  - M5-O3: Thiết lập quy trình bảo trì Iceberg: compaction (rewrite_data_files), expire snapshots và xóa file mồ côi (remove_orphan_files)
- **Tiêu chí hoàn thành Milestone:** Tối ưu câu lệnh join trên tập dữ liệu skew làm giảm thời gian chạy ít nhất 30%; giải quyết triệt để vấn đề small files thông qua call procedure compaction trên Iceberg.
- **Khái niệm bổ sung (ngoài KB):** `spark-aqe-skew-join-optimization`, `spark-catalyst-optimizer-tuning`, `iceberg-compaction-maintenance-procedures`

#### M6. Tầng Gold & Kiểm thử Chất lượng Dữ liệu với dbt-core trên Spark/Iceberg (420 phút | Phụ thuộc: M5)
- **Mô tả:** Mô hình hóa tầng Gold phục vụ Business Intelligence bằng dbt-core (dbt-spark / dbt-iceberg adapter), xây dựng data marts và triển khai data contracts cùng test suites tự động.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M6-O1: Cài đặt và cấu hình dbt-core kết nối đến Spark Thrift Server / Iceberg catalog
  - M6-O2: Xây dựng các dbt model (views, incremental/iceberg tables) tổng hợp chỉ số kinh doanh tại tầng Gold
  - M6-O3: Triển khai bộ kiểm thử chất lượng dữ liệu dbt (not null, unique, relationships, accepted values và custom generic tests)
- **Tiêu chí hoàn thành Milestone:** Lệnh `dbt build` chạy thành công toàn bộ models tầng Gold và 100% tests kiểm tra tính toàn vẹn dữ liệu vượt qua gate kiểm định chất lượng.
- **Khái niệm bổ sung (ngoài KB):** `dbt-core-spark-iceberg-adapter`, `lakehouse-medallion-gold-modeling`, `dbt-data-quality-testing-assertions`

#### M7. Tích hợp Pipeline Toàn diện (End-to-End) & Tài liệu Hóa Vận hành (420 phút | Phụ thuộc: M6)
- **Mô tả:** Ghép nối toàn bộ chuỗi Medallion từ MinIO Streaming Bronze -> Silver Upsert -> Gold Aggregation -> dbt Data Gate; đóng gói benchmark và viết kịch bản vận hành thực tế.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M7-O1: Tích hợp luồng end-to-end tự động chạy từ ingestion streaming đến dbt gold models
  - M7-O2: Xây dựng kịch bản kiểm thử giả lập lỗi (data drift, spike traffic, node failure) và kiểm chứng cơ chế tự phục hồi
  - M7-O3: Đóng gói toàn bộ repository kèm Docker Compose, Spark jobs, dbt project và tài liệu kiến trúc kỹ thuật
- **Tiêu chí hoàn thành Milestone:** Dự án hoàn chỉnh chạy qua 1 kịch bản demo end-to-end: streaming data phát sinh được ingest, làm sạch, biến đổi sang Gold, dbt test pass và xuất báo cáo phân tích.
- **Khái niệm bổ sung (ngoài KB):** `lakehouse-end-to-end-pipeline-integration`, `lakehouse-disaster-recovery-data-drift`, `data-engineering-architecture-documentation`

---

## M-07 — Hệ thống MLOps & LLMOps Production: vLLM Serving, Eval Harness & Drift Monitoring

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `ADVANCED`
- **Mô tả mục tiêu:** Triển khai pipeline serving LLM/ML chuẩn production với vLLM continuous batching, Prompt & Model Registry, Eval Harness tự động (pass@1, faithfulness, latency p95), guardrails chống prompt injection và Prometheus/Grafana drift alerting trong 8 tuần.
- **Khung thời gian:** `2026-11-02` → `2026-12-28`
- **Quỹ thời gian rảnh:** MODE_B: monday 20:00–22:00, thursday 20:00–22:00, sunday 09:00–12:00 | Ngày nghỉ: wednesday, saturday
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE 8 tuần bao phủ toàn diện mục tiêu LLMOps/MLOps Production: Serving tối ưu với vLLM PagedAttention, Prompt & Model Registry có versioning checksum, Eval Harness tự động trong CI/CD, Guardrails runtime chống injection và hệ thống cảnh báo Prometheus/Grafana drift monitoring.
- **Tổng quan Milestone Plan:** 6 milestones | Tổng effort: 2880 phút (48.0 giờ)

### Danh sách Milestones

#### M1. vLLM Production Serving & Tối ưu Throughput với PagedAttention (480 phút | Phụ thuộc: Không)
- **Mô tả:** Cấu hình và benchmark engine phục vụ vLLM với PagedAttention và continuous batching; đóng gói container GPU và đo lường TTFT, TPOT, tail latency p95 dưới tải giả lập.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M1-O1: Triển khai vLLM engine với continuous batching và tối ưu tham số cấp phát KV-cache PagedAttention
  - M1-O2: Đóng gói service serving GPU trong Docker và cấu hình OpenAI-compatible API gateway
  - M1-O3: Thực hiện benchmark đo lường Time-To-First-Token (TTFT), Time-Per-Output-Token (TPOT) và p95 latency khi tăng concurrency
- **Tiêu chí hoàn thành Milestone:** Server vLLM phản hồi OpenAI-compatible endpoint đạt p95 TTFT < 800ms và throughput duy trì ổn định không bị OOM dưới 50 concurrent requests giả lập.
- **Khái niệm đã xác minh (KB):** `fastapi-routing-pydantic`
- **Khái niệm bổ sung (ngoài KB):** `vllm-engine-architecture`, `paged-attention-kv-cache-optimization`, `gpu-containerization-nvidia-runtime`, `llm-latency-throughput-benchmarking`

#### M2. Prompt & Model Registry với Checksum Versioning (420 phút | Phụ thuộc: M1)
- **Mô tả:** Xây dựng hệ thống quản lý Prompt Template và Model Artifacts có đánh phiên bản bất biến bằng checksum hash, quản trị metadata và liên kết schema xác thực dữ liệu.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M2-O1: Thiết kế Prompt Registry lưu trữ template, hyperparameters và checksum versioning bất biến
  - M2-O2: Tích hợp Model Registry theo dõi lineage của weights, cấu hình quantization (AWQ/GPTQ) và artifact metadata
  - M2-O3: Tích hợp middleware xác thực cấu trúc output Pydantic v2 chặt chẽ trước khi trả về client
- **Tiêu chí hoàn thành Milestone:** Mọi thay đổi prompt hoặc model metadata đều tự động sinh checksum định danh duy nhất; gateway từ chối chạy khi checksum không khớp phiên bản đã đăng ký.
- **Khái niệm đã xác minh (KB):** `fastapi-routing-pydantic`, `ai-llm-structured-rag-agents`
- **Khái niệm bổ sung (ngoài KB):** `prompt-registry-versioning-checksums`, `model-lineage-artifact-store`, `structured-output-guardrails`

#### M3. Eval Harness Tự động & Regression Testing Gate trong CI/CD (540 phút | Phụ thuộc: M2)
- **Mô tả:** Thiết kế harness kiểm thử chất lượng LLM tự động với pass@1, faithfulness, answer relevancy và tích hợp regression gate vào pipeline CI/CD.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M3-O1: Xây dựng tập testset chuẩn hóa và metric harness đo lường pass@1, faithfulness và context recall
  - M3-O2: Cấu hình LLM-as-a-judge kết hợp deterministic assertions để giảm thiểu bias đánh giá
  - M3-O3: Thiết lập GitHub Actions/GitLab CI eval gate tự động chặn deployment nếu điểm chất lượng suy giảm quá 3%
- **Tiêu chí hoàn thành Milestone:** Pipeline CI tự động kích hoạt bộ Eval Harness trên pull request, xuất báo cáo điểm pass@1/faithfulness và fail build nếu vi phạm ngưỡng regression gate.
- **Khái niệm đã xác minh (KB):** `ai-llm-structured-rag-agents`, `ml-supervised-evaluation`
- **Khái niệm bổ sung (ngoài KB):** `llm-eval-harness-frameworks`, `ragas-faithfulness-evaluation`, `automated-eval-ci-cd-regression-gates`

#### M4. Guardrails Chống Prompt Injection & Kiểm Soát An Toàn Runtime (450 phút | Phụ thuộc: M2)
- **Mô tả:** Triển khai lớp kiểm duyệt 2 chiều (input/output) chặn prompt injection, jailbreak, rò rỉ PII và can thiệp nội dung độc hại trên luồng streaming.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M4-O1: Tích hợp guardrails layer kiểm duyệt input bằng regex signatures, heuristic rules và classification model
  - M4-O2: Phát hiện và cô lập prompt injection vectors và jailbreak attempts trước khi đưa vào context vLLM
  - M4-O3: Lọc PII và kiểm soát hallucination/safety trên token streaming response mà không làm tăng TTFT vượt 15%
- **Tiêu chí hoàn thành Milestone:** Vượt qua test suite gồm 100 mẫu tấn công jailbreak/prompt injection với tỷ lệ chặn >= 98% và độ trễ bổ sung ở gateway < 50ms.
- **Khái niệm đã xác minh (KB):** `ai-llm-structured-rag-agents`
- **Khái niệm bổ sung (ngoài KB):** `prompt-injection-defense-mechanisms`, `pii-redaction-and-content-filtering`, `streaming-guardrail-interceptor`

#### M5. Prometheus & Grafana Drift Alerting, Token Cost & Operational Monitoring (510 phút | Phụ thuộc: M1, M3, M4)
- **Mô tả:** Thu thập metrics runtime (KV-cache usage, queue depth, p95/p99 latency), giám sát data/embedding drift bằng kiểm định thống kê và thiết lập dashboard cảnh báo Grafana.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M5-O1: Xuất runtime metrics chuẩn Prometheus từ vLLM và gateway (GPU memory, request queue size, token generation speed)
  - M5-O2: Thiết lập pipeline phát hiện data drift và semantic embedding drift sử dụng kiểm định phân phối (KS-test / PSI)
  - M5-O3: Xây dựng Grafana Dashboard và Alertmanager cảnh báo khi tail latency p95 > 2s, token cost tăng đột biến hoặc drift vượt ngưỡng
- **Tiêu chí hoàn thành Milestone:** Grafana hiển thị đầy đủ throughput, latency percentiles, chi phí token real-time và Alertmanager kích hoạt webhook cảnh báo chính xác khi mô phỏng embedding drift hoặc request spike.
- **Khái niệm đã xác minh (KB):** `ml-supervised-evaluation`, `sys-caching-redis-queues`
- **Khái niệm bổ sung (ngoài KB):** `prometheus-metrics-exporter-vllm`, `grafana-llm-ops-dashboards`, `statistical-drift-detection-ks-psi`, `alertmanager-incident-routing`

#### M6. Vận hành Production Gateway Tổng thể: End-to-End Stress Test & Runbook (480 phút | Phụ thuộc: M5)
- **Mô tả:** Tích hợp toàn diện Serving, Registry, CI Eval Gate, Guardrails và Monitoring thành hệ sinh thái production hoàn chỉnh; thực hiện chaos/stress testing và hoàn thiện tài liệu vận hành.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M6-O1: Hợp nhất toàn bộ các thành phần thành kiến trúc LLMOps Gateway đồng nhất sẵn sàng cho môi trường production
  - M6-O2: Tiến hành stress test tải lớn kết hợp kịch bản worker failure để thẩm định cơ chế auto-recovery và circuit breaker
  - M6-O3: Xây dựng Runbook vận hành chuẩn Staff MLOps: xử lý GPU memory fragmentation, rollback prompt/model và SLA escalation
- **Tiêu chí hoàn thành Milestone:** Hệ thống vượt qua 4 giờ stress testing liên tục ở tải cao, không rò rỉ tài nguyên, eval CI gate chặn thành công bản release lỗi và runbook giải quyết triệt để 3 sự cố giả lập.
- **Khái niệm đã xác minh (KB):** `fastapi-routing-pydantic`, `ai-llm-structured-rag-agents`, `sys-caching-redis-queues`
- **Khái niệm bổ sung (ngoài KB):** `llm-gateway-production-hardening`, `stress-testing-locust-llm`, `mlops-staff-incident-runbook`

---

## M-08 — Full-Stack Next.js App Router, React Server Components & PostgreSQL Indexing

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `INTERMEDIATE`
- **Mô tả mục tiêu:** Xây dựng ứng dụng SaaS multi-tenant với Next.js App Router, Server Actions, Auth/RBAC session bảo mật, tối ưu PostgreSQL Row-Level Security + B-Tree/GIN index, caching revalidation và Playwright E2E testing trong 4 tuần.
- **Khung thời gian:** `2026-11-02` → `2026-11-30`
- **Quỹ thời gian rảnh:** MODE_B: monday 19:30–21:30, tuesday 19:30–21:30, friday 19:30–21:30, saturday 14:00–17:00 | Ngày nghỉ: thursday, sunday
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE bao phủ toàn diện 4 tuần (tổng nỗ lực 36 giờ, khớp chính xác cam kết 9 giờ/tuần) từ thiết kế CSDL PostgreSQL RLS và B-Tree/GIN Indexing, xây dựng kiến trúc Next.js App Router RSC với Session/RBAC, bảo mật Server Actions cùng cơ chế Caching Revalidation, đến tự động hóa kiểm thử End-to-End với Playwright đáp ứng chuẩn p95 < 30ms.
- **Tổng quan Milestone Plan:** 4 milestones | Tổng effort: 2160 phút (36.0 giờ)

### Danh sách Milestones

#### M1. Thiết kế Schema Multi-tenant, PostgreSQL RLS & Chiến lược Lập chỉ mục Indexing (540 phút | Phụ thuộc: Không)
- **Mô tả:** Xây dựng schema cơ sở dữ liệu quan hệ multi-tenant với PostgreSQL, áp dụng Row-Level Security (RLS) để cô lập dữ liệu người thuê và tối ưu hóa truy vấn với B-Tree/GIN index.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M1-O1: Thiết kế cấu trúc bảng multi-tenant tách biệt theo tenant_id đạt chuẩn chuẩn hóa quan hệ
  - M1-O2: Cấu hình và kiểm thử các chính sách PostgreSQL Row-Level Security (RLS) để ngăn chặn rò rỉ dữ liệu chéo giữa các tenant
  - M1-O3: Phân tích kế hoạch thực thi EXPLAIN ANALYZE và tạo B-Tree/GIN index phù hợp để đưa p95 latency truy vấn về dưới 30ms
- **Tiêu chí hoàn thành Milestone:** Tất cả các truy vấn tenant-scoped khi chạy EXPLAIN ANALYZE đều áp dụng RLS policy hợp lệ, chi phí index scan tối ưu và thời gian thực thi p95 đạt dưới 30ms trên tập dữ liệu mẫu.
- **Khái niệm đã xác minh (KB):** `sql-relational-modeling`
- **Khái niệm bổ sung (ngoài KB):** `postgresql-row-level-security`, `postgresql-indexing-btree-gin`, `explain-analyze-query-optimization`

#### M2. Kiến trúc Next.js App Router, React Server Components & Quản lý Session/RBAC (540 phút | Phụ thuộc: M1)
- **Mô tả:** Xây dựng nền tảng ứng dụng Next.js với kiến trúc React Server Components (RSC), giải quyết triệt để waterfall fetching và triển khai hệ thống xác thực session an toàn với RBAC.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M2-O1: Phân tách ranh giới Server Components và Client Components, quản lý serialization an toàn và loại bỏ vấn đề waterfall fetch
  - M2-O2: Cấu hình phiên làm việc bảo mật với HttpOnly cookie, middleware xác thực và phân quyền truy cập theo vai trò (RBAC)
  - M2-O3: Thiết lập ranh giới bảo mật cấp ứng dụng nhằm ngăn ngừa triệt để lỗ hổng IDOR và cross-tenant access
- **Tiêu chí hoàn thành Milestone:** Xây dựng thành công hệ thống routing và middleware xác thực phân quyền RBAC; các Server Components nạp dữ liệu song song không bị blocking waterfall và session được bảo vệ an toàn trong HttpOnly cookie.
- **Khái niệm đã xác minh (KB):** `backend-auth-jwt-security`, `ts-strict-type-system`
- **Khái niệm bổ sung (ngoài KB):** `nextjs-app-router-rsc-architecture`, `rsc-serialization-boundaries`, `nextjs-middleware-rbac-session`

#### M3. Server Actions An Toàn, Cơ Chế Caching Đa Tầng & Revalidation (540 phút | Phụ thuộc: M2)
- **Mô tả:** Xây dựng các luồng mutation dữ liệu thông qua Server Actions với cơ chế phòng thủ CSRF/IDOR và điều phối các tầng cache của Next.js (Request Memoization, Data Cache, Full Route Cache).
- **Chuẩn đầu ra (Learning Outcomes):**
  - M3-O1: Triển khai các Server Actions an toàn cho luồng cập nhật dữ liệu với xác thực schema chặt chẽ và phòng chống CSRF
  - M3-O2: Kiểm soát cơ chế lưu trữ đệm 4 tầng của Next.js (fetch cache, memoization, full route cache) và kỹ thuật revalidatePath / revalidateTag
  - M3-O3: Đo lường và tối ưu hóa hiệu năng tải trang với Lighthouse để kiểm soát Time to First Byte (TTFB) và Cumulative Layout Shift (CLS)
- **Tiêu chí hoàn thành Milestone:** Toàn bộ mutation thực hiện qua Server Actions có xác thực đầu vào, dữ liệu được revalidate tức thì qua on-demand tag/path và điểm hiệu năng Lighthouse đạt chuẩn xanh.
- **Khái niệm bổ sung (ngoài KB):** `nextjs-server-actions-security`, `nextjs-caching-revalidation-lifecycle`, `web-vitals-lighthouse-auditing`

#### M4. Tích Hợp Toàn Diện SaaS Multi-Tenant & Playwright E2E Testing (540 phút | Phụ thuộc: M3)
- **Mô tả:** Tích hợp hoàn chỉnh workspace multi-tenant, viết bộ kiểm thử End-to-End với Playwright kiểm tra luồng phân quyền, chống rò rỉ dữ liệu tenant và nghiệm thu hiệu năng toàn hệ thống.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M4-O1: Hoàn thiện ứng dụng SaaS workspace multi-tenant kết nối đồng bộ từ UI, Server Actions đến PostgreSQL RLS
  - M4-O2: Viết kịch bản kiểm thử tự động Playwright E2E bao phủ các ca kiểm thử bảo mật cô lập tenant, RBAC và các luồng nghiệp vụ cốt lõi
  - M4-O3: Chạy tải và nghiệm thu hiệu năng toàn diện đảm bảo p95 query < 30ms và hệ thống vận hành ổn định không phát sinh lỗi rò rỉ dữ liệu
- **Tiêu chí hoàn thành Milestone:** Bộ test suite Playwright E2E vượt qua 100% các ca kiểm thử multi-tenant và RBAC; số liệu đo kiểm chứng minh p95 latency truy vấn đạt dưới 30ms trong môi trường tích hợp.
- **Khái niệm bổ sung (ngoài KB):** `playwright-e2e-saas-testing`, `multi-tenant-isolation-validation`, `production-performance-benchmarking`

---

## M-09 — Full-Stack Next.js App Router, React Server Components & PostgreSQL Indexing

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `INTERMEDIATE`
- **Mô tả mục tiêu:** Xây dựng ứng dụng SaaS multi-tenant với Next.js App Router, Server Actions, Auth/RBAC session bảo mật, tối ưu PostgreSQL Row-Level Security + B-Tree/GIN index, caching revalidation và Playwright E2E testing trong 4 tuần.
- **Khung thời gian:** `2026-11-02` → `2026-11-30`
- **Quỹ thời gian rảnh:** MODE_B: monday 19:30–21:30, tuesday 19:30–21:30, friday 19:30–21:30, saturday 14:00–17:00 | Ngày nghỉ: thursday, sunday
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE 4 tuần (tương ứng 36 giờ nỗ lực học tập, 9 giờ/tuần) bao phủ trọn vẹn toàn bộ mục tiêu xây dựng SaaS multi-tenant: từ thiết kế cơ sở dữ liệu PostgreSQL chuẩn hóa có RLS và tối ưu B-Tree/GIN index, qua kiến trúc Next.js App Router/RSC triệt tiêu waterfall, bảo mật Server Actions/RBAC và caching đa tầng, đến kiểm thử tự động hóa Playwright E2E và đo kiểm hiệu năng production.
- **Tổng quan Milestone Plan:** 4 milestones | Tổng effort: 2160 phút (36.0 giờ)

### Danh sách Milestones

#### M1. Thiết kế Lược đồ Multi-tenant, PostgreSQL Row-Level Security (RLS) & Tối ưu B-Tree/GIN Index (540 phút | Phụ thuộc: Không)
- **Mô tả:** Xây dựng nền tảng cơ sở dữ liệu quan hệ chuẩn hóa cho SaaS multi-tenant, cô lập dữ liệu người dùng/workspace thông qua PostgreSQL RLS và tối ưu hóa hiệu năng truy vấn bằng chỉ mục chuyên sâu.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M1-O1: Thiết kế lược đồ quan hệ PostgreSQL cho SaaS multi-tenant với bảng tenants, users, memberships và workspaces chuẩn 3NF
  - M1-O2: Cấu hình và kiểm thử chính sách Row-Level Security (RLS) bằng app.current_tenant_id để ngăn chặn tuyệt đối rò rỉ dữ liệu cross-tenant
  - M1-O3: Đánh chỉ mục B-Tree (composite indexes) và GIN (full-text search / JSONB) dựa trên phân tích EXPLAIN (ANALYZE, BUFFERS) đạt p95 query latency < 30ms
- **Tiêu chí hoàn thành Milestone:** Tạo migration hoàn chỉnh kèm bộ SQL script thiết lập RLS policy; chạy test suite SQL chứng minh session của Tenant A không thể đọc/ghi dữ liệu của Tenant B; thực thi EXPLAIN ANALYZE với 100,000 dòng dữ liệu mẫu chứng minh truy vấn lọc kết hợp sử dụng Index Scan thay vì Seq Scan và p95 latency < 30ms.
- **Khái niệm đã xác minh (KB):** `sql-relational-modeling`
- **Khái niệm bổ sung (ngoài KB):** `postgresql-row-level-security`, `postgresql-btree-gin-indexing`, `sql-explain-analyze-optimization`

#### M2. Kiến trúc Next.js App Router, React Server Components (RSC) & Data Fetching không Waterfall (540 phút | Phụ thuộc: M1)
- **Mô tả:** Làm chủ kiến trúc App Router, cơ chế tuần tự hóa (serialization) của React Server Components, ranh giới Client/Server boundary và kỹ thuật data fetching song song để triệt tiêu vấn đề waterfall fetch.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M2-O1: Phân tách ranh giới 'use client' và Server Components theo nguyên tắc cây phân cấp, truyền props tuần tự hóa an toàn
  - M2-O2: Tổ chức routing phức tạp với Route Groups, Parallel Routes, Intercepting Routes cho trải nghiệm workspace modal/dashboard
  - M2-O3: Áp dụng kỹ thuật fetch song song với Promise.all và React Suspense boundary để loại bỏ hoàn toàn hiện tượng network waterfall
- **Tiêu chí hoàn thành Milestone:** Xây dựng dashboard multi-tenant với layout lồng nhau và Suspense streaming; cấu trúc component không bị leak code server sang client bundle; kiểm tra Network tab trên trình duyệt chứng minh các truy vấn dữ liệu độc lập chạy đồng thời và TTFB cải thiện rõ rệt.
- **Khái niệm đã xác minh (KB):** `ts-strict-type-system`
- **Khái niệm bổ sung (ngoài KB):** `nextjs-app-router-architecture`, `react-server-components-serialization`, `parallel-data-fetching-suspense-streaming`

#### M3. Xác thực Phiên làm việc (Session/RBAC), Server Actions An toàn & Next.js Caching/Revalidation (540 phút | Phụ thuộc: M2)
- **Mô tả:** Cài đặt luồng định danh người dùng an toàn với Session/HttpOnly cookie, kiểm soát quyền truy cập theo vai trò (RBAC), bảo vệ Server Actions chống CSRF/IDOR và điều khiển 4 tầng cache trong Next.js.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M3-O1: Cài đặt luồng Auth và phân quyền theo vai trò (RBAC) với Session bảo mật trong HttpOnly cookie, middleware bảo vệ route và context multi-tenant
  - M3-O2: Xây dựng Server Actions với Zod schema validation, kiểm tra quyền sở hữu tài nguyên tại server-side để triệt tiêu lỗ hổng IDOR và CSRF
  - M3-O3: Làm chủ 4 tầng cache của Next.js (Request Memoization, Data Cache, Full Route Cache, Router Cache) và cơ chế revalidateTag/revalidatePath
- **Tiêu chí hoàn thành Milestone:** Triển khai hoàn tất module Auth & Workspace Management; chứng minh middleware và Server Actions từ chối các request giả mạo ID hoặc thiếu quyền với mã lỗi chuẩn; gọi revalidateTag sau khi tạo mới tài nguyên và xác nhận dữ liệu trên UI cập nhật ngay lập tức mà không cần reload trang.
- **Khái niệm đã xác minh (KB):** `backend-auth-jwt-security`, `ts-strict-type-system`
- **Khái niệm bổ sung (ngoài KB):** `nextjs-server-actions-security`, `nextjs-four-layer-caching-revalidation`, `rbac-multi-tenant-authorization`

#### M4. Kiểm thử End-to-End Playwright, Đo kiểm Hiệu năng Production & Hoàn thiện Hệ thống SaaS (540 phút | Phụ thuộc: M3)
- **Mô tả:** Tự động hóa kiểm thử đa người dùng bằng Playwright E2E, rà soát bảo mật tenant isolation, kiểm tra chỉ số Web Vitals/Lighthouse và tinh chỉnh toàn diện hệ thống sẵn sàng triển khai thực tế.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M4-O1: Viết test suite Playwright E2E mô phỏng đồng thời 2 người dùng thuộc 2 tenant khác nhau để kiểm tra toàn vẹn ranh giới dữ liệu
  - M4-O2: Kiểm thử tự động các luồng quan trọng: Đăng nhập -> Chuyển đổi Workspace -> Thao tác CRUD qua Server Actions -> Xác nhận revalidation UI
  - M4-O3: Đo kiểm Core Web Vitals (LCP, FID/INP, CLS) bằng Lighthouse, tối ưu bundle size và xác nhận chỉ số p95 query latency đạt chuẩn dưới 30ms trên môi trường production-like
- **Tiêu chí hoàn thành Milestone:** Toàn bộ kịch bản Playwright E2E chạy thành công trong CI pipeline; có báo cáo Lighthouse đạt điểm Performance > 90 và Accessibility > 90; tệp log đo p95 query latency xác nhận < 30ms dưới tải kiểm thử multi-tenant.
- **Khái niệm đã xác minh (KB):** `ts-strict-type-system`
- **Khái niệm bổ sung (ngoài KB):** `playwright-e2e-testing-multi-tenant`, `web-vitals-lighthouse-optimization`, `saas-production-readiness-audit`

---

## M-10 — Embedded Rust #![no_std] & RTOS Embassy cho Vi điều khiển ARM Cortex-M

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `INTERMEDIATE`
- **Mô tả mục tiêu:** Làm chủ Rust #![no_std], Ownership/Lifetimes trên bộ nhớ tĩnh, HAL/PAC thanh ghi, DMA/SPI/I2C, Embassy async executor, RTIC interrupt scheduling và debug phần cứng bằng probe-rs/defmt trong 8 tuần.
- **Khung thời gian:** `2026-11-02` → `2026-12-28`
- **Quỹ thời gian rảnh:** MODE_B: monday 20:00–22:00, wednesday 20:00–22:00, saturday 14:00–17:00 | Ngày nghỉ: friday, sunday
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE 8 tuần (3.060 phút ~ 51 giờ) bao phủ toàn bộ mục tiêu Embedded Rust cho vi điều khiển ARM Cortex-M: từ nền tảng #![no_std], memory layout, PAC/HAL, zero-copy SPI/DMA, lập trình ngắt RTIC cho đến async runtime Embassy và dự án firmware telemetry thực tế.
- **Tổng quan Milestone Plan:** 6 milestones | Tổng effort: 3060 phút (51.0 giờ)

### Danh sách Milestones

#### M1. Môi trường Embedded Rust, Công cụ Debug probe-rs & Mô hình bộ nhớ #![no_std] (420 phút | Phụ thuộc: Không)
- **Mô tả:** Thiết lập toolchain cross-compile target thumbv7em-none-eabihf / thumbv6m-none-eabi, cấu hình memory.x, liên kết cortex-m-rt, triển khai panic handler tùy biến và logging siêu nhẹ với defmt qua probe-rs/RTT.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M1-O1: Cấu hình cargo config, target cross-compilation, linker script memory.x và cortex-m-rt tối ưu flash/RAM
  - M1-O2: Cài đặt #[panic_handler] an toàn trong môi trường #![no_std] và tích hợp defmt để log chẩn đoán qua RTT với probe-rs
  - M1-O3: Phân tích mô hình bộ nhớ tĩnh, stack layout và cơ chế kiểm soát con trỏ raw pointer so với reference an toàn trong Rust
- **Tiêu chí hoàn thành Milestone:** Flash thành công firmware tối giản lên vi điều khiển (hoặc Renode emulator), in log chào mừng qua defmt-rtt bằng lệnh cargo run/probe-rs run và kích hoạt kiểm tra panic bắt được địa chỉ code.
- **Khái niệm bổ sung (ngoài KB):** `cortex-m-rt`, `probe-rs`, `defmt-rtt`, `memory-layout-no-std`, `cross-compilation-toolchain`

#### M2. PAC, HAL thanh ghi & Quản lý Ngoại vi qua Ownership/Typestate (480 phút | Phụ thuộc: M1)
- **Mô tả:** Khám phá tầng Peripheral Access Crate (PAC) sinh từ SVD, thiết kế Zero-Cost Abstraction sử dụng mẫu hình Typestate Pattern để ép buộc tính an toàn cấu hình chân GPIO và Clock tại thời điểm biên dịch.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M2-O1: Đọc và thao tác trực tiếp thanh ghi vi điều khiển qua svd2rust sinh PAC bằng phương thức modify/write/read an toàn
  - M2-O2: Ứng dụng Ownership và Typestate pattern để chuyển đổi trạng thái GPIO (Input -> Output -> Alternate) loại trừ lỗi runtime
  - M2-O3: Cấu hình cây xung nhịp hệ thống (RCC / Clocks) và tích hợp crate embedded-hal trừu tượng hóa phần cứng
- **Tiêu chí hoàn thành Milestone:** Viết driver cấu hình chân LED và nút bấm hoàn toàn bằng Typestate Pattern; mã nguồn từ chối biên dịch nếu gọi hàm ghi trước khi chân được khởi tạo chế độ Output.
- **Khái niệm bổ sung (ngoài KB):** `peripheral-access-crate-pac`, `typestate-pattern`, `embedded-hal`, `zero-cost-abstractions`

#### M3. Giao tiếp Ngoại vi SPI/I2C & Chuyển giao Bộ nhớ Zero-Copy DMA (540 phút | Phụ thuộc: M2)
- **Mô tả:** Lập trình driver giao tiếp cảm biến qua SPI và I2C, giải quyết bài toán mượn bộ nhớ tĩnh và quản lý vòng đời (lifetimes) của buffer khi truyền nhận dữ liệu DMA không blocking và zero-copy.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M3-O1: Viết driver đọc dữ liệu cảm biến tuân thủ embedded-hal traits cho giao tiếp SPI/I2C
  - M3-O2: Quản lý con trỏ buffer và static lifetime an toàn trong các giao dịch DMA, tránh data race giữa CPU và DMA engine
  - M3-O3: Đo kiểm tín hiệu giao tiếp phần cứng bằng logic analyzer hoặc trace mô phỏng trong Renode
- **Tiêu chí hoàn thành Milestone:** Đọc thành công mẫu dữ liệu cảm biến đa byte qua SPI bằng DMA buffer cố định, xác thực dữ liệu qua logic analyzer/defmt mà không phát sinh copy bộ nhớ trung gian.
- **Khái niệm bổ sung (ngoài KB):** `spi-i2c-drivers`, `dma-zero-copy-buffers`, `static-lifetimes-hardware`, `logic-analyzer-debugging`

#### M4. Ngắt Ngoại vi (NVIC), RTIC Framework & Mô hình Concurrency An toàn (480 phút | Phụ thuộc: M3)
- **Mô tả:** Xử lý ngắt phần cứng qua NVIC của ARM Cortex-M, chống deadlock bằng RTIC (Real-Time Interrupt-driven Concurrency) với cơ chế Resource Lock dựa trên trần ưu tiên (Priority Ceiling Protocol).
- **Chuẩn đầu ra (Learning Outcomes):**
  - M4-O1: Cấu hình vector ngắt NVIC và viết hàm ngắt an toàn sử dụng atomic flags và critical section
  - M4-O2: Áp dụng kiến trúc RTIC để chia sẻ tài nguyên giữa các mức ưu tiên ngắt khác nhau mà không bị deadlock
  - M4-O3: Đo đạc và phân tích độ trễ ngắt (interrupt latency) cùng hiện tượng timing jitter trên chân đo xung chuyên dụng
- **Tiêu chí hoàn thành Milestone:** Chạy ứng dụng RTIC đa tác vụ ưu tiên khác nhau trên board, chứng minh việc truy cập tài nguyên dùng chung diễn ra trơn tru không deadlock và jitter đo được dưới ngưỡng 5 microgiây.
- **Khái niệm bổ sung (ngoài KB):** `cortex-m-nvic-interrupts`, `rtic-framework`, `priority-ceiling-protocol`, `interrupt-timing-jitter`

#### M5. Embassy Async Runtime & Lập trình Vi điều khiển Bất đồng bộ (540 phút | Phụ thuộc: M4)
- **Mô tả:** Nghiên cứu kiến trúc Cooperative Multitasking của Embassy async executor, cơ chế Waker phần cứng, WFE/WFI tiết kiệm năng lượng và các kênh giao tiếp Task (Channel, Signal, Mutex).
- **Chuẩn đầu ra (Learning Outcomes):**
  - M5-O1: Nắm vững nguyên lý hoạt động của Embassy Executor không cấp phát động (heapless) trên nền ARM Cortex-M
  - M5-O2: Triển khai các async task đồng thời với macro #[embassy_executor::task] và quản lý dừng/đánh thức bằng hardware interrupt wakers
  - M5-O3: Truyền nhận thông điệp bất đồng bộ an toàn giữa các task thông qua embassy-sync Channels và Signals
- **Tiêu chí hoàn thành Milestone:** Xây dựng hệ thống gồm 3 task độc lập chạy đồng thời trên Embassy executor (chớp LED hẹn giờ, đọc nút bấm bất đồng bộ, xử lý hàng đợi sự kiện) mà không sử dụng dynamic memory allocation.
- **Khái niệm bổ sung (ngoài KB):** `embassy-async-executor`, `hardware-interrupt-waker`, `embassy-sync-primitives`, `low-power-wfe-wfi`

#### M6. Dự án Tổng hợp: Firmware Telemetry Bất đồng bộ với SPI/DMA & Embassy (600 phút | Phụ thuộc: M5)
- **Mô tả:** Tích hợp toàn diện kiến thức để xây dựng firmware hoàn chỉnh trên STM32F4/RP2040: thu thập dữ liệu cảm biến định kỳ qua SPI/DMA, định dạng gói tin telemetry và truyền phát non-blocking qua UART/USB.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M6-O1: Kiến trúc hóa firmware nhúng đa module kết hợp Embassy Time, Async SPI/DMA và UART telemetry
  - M6-O2: Thiết kế buffer vòng (ring buffer) zero-copy với heapless data structures đảm bảo tính an toàn bộ nhớ tuyệt đối
  - M6-O3: Kiểm thử toàn diện bằng probe-rs, đo dòng điện/tiêu thụ năng lượng và đóng gói tài liệu firmware chuẩn công nghiệp
- **Tiêu chí hoàn thành Milestone:** Firmware chạy liên tục tối thiểu 30 phút trên phần cứng thật/Renode, xuất luồng telemetry định kỳ qua UART với jitter ổn định, không có panic, không leak bộ nhớ và buffer DMA luôn được giải phóng an toàn.
- **Khái niệm bổ sung (ngoài KB):** `embassy-async-dma`, `heapless-data-structures`, `telemetry-streaming-firmware`, `hardware-in-the-loop-validation`

---

## M-11 — Hệ thống Phân tán hiệu năng cao với Go: Raft Consensus, gRPC & Distributed Tracing

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `ADVANCED`
- **Mô tả mục tiêu:** Thiết kế và cài đặt cụm lưu trữ Key-Value chịu lỗi dùng Go, Raft leader election & log replication, gRPC streaming, circuit breaker và OpenTelemetry distributed tracing trong 4 tuần. Cần xử lý race condition với Goroutines/Channels và benchmark p99 latency.
- **Khung thời gian:** `2026-11-02` → `2026-11-30`
- **Quỹ thời gian rảnh:** MODE_B: monday 19:30–21:30, tuesday 19:30–21:30, thursday 19:30–21:30, saturday 09:00–12:00 | Ngày nghỉ: wednesday, sunday
- **Tóm tắt phạm vi lộ trình:** Lộ trình Full Scope kéo dài 4 tuần (tương đương 36 giờ nỗ lực theo cam kết 9 giờ/tuần), bao phủ toàn diện từ nền tảng đồng thuận Raft (Leader Election, Log Replication, Partition Tolerance, Compaction), tầng giao tiếp gRPC Streaming & Resiliency (Circuit Breaker), đến Observability chuẩn công nghiệp (OpenTelemetry Distributed Tracing) và Benchmark p99 Latency trên môi trường Docker cụm 3 node.
- **Tổng quan Milestone Plan:** 4 milestones | Tổng effort: 2160 phút (36.0 giờ)

### Danh sách Milestones

#### M1. Cơ chế Đồng thuận Raft: Leader Election & State Machine Replication (540 phút | Phụ thuộc: Không)
- **Mô tả:** Nghiên cứu đặc tả Raft consensus paper, triển khai State Machine trong Go với các trạng thái Follower, Candidate, Leader. Cài đặt thuật toán RequestVote, AppendEntries RPC logic, Heartbeat timer, và đồng bộ hóa qua Goroutines/Channels không để xảy ra race condition.
- **Chuẩn đầu ra (Learning Outcomes):**
  - Cài đặt thành công vòng đời trạng thái Raft (Follower, Candidate, Leader) và cơ chế ngẫu nhiên hóa election timeout để phòng tránh split-vote.
  - Xây dựng cơ chế Replicated Log đảm bảo tính an toàn (safety property), commit log index và áp dụng lệnh vào Key-Value State Machine cục bộ.
  - Thiết kế cấu trúc concurrency an toàn bằng Goroutines, Channels, sync.RWMutex và context timeout, vượt qua kiểm tra 'go test -race'.
- **Tiêu chí hoàn thành Milestone:** Vượt qua toàn bộ unit test mô phỏng bầu cử và sao chép log; lệnh 'go test -race -count=10 ./raft/...' không phát hiện bất kỳ data race nào; cụm 3 node tự động bầu leader mới khi kill leader hiện tại trong vòng 300ms.
- **Khái niệm bổ sung (ngoài KB):** `raft-consensus-algorithm`, `leader-election-term`, `log-replication-state-machine`, `go-race-detector-concurrency`

#### M2. Khả năng Chịu lỗi Nâng cao: Network Partition, Log Compaction & Snapshotting (540 phút | Phụ thuộc: M1)
- **Mô tả:** Triển khai cơ chế Snapshotting và InstallSnapshot RPC để nén log định kỳ, giải phóng bộ nhớ. Giả lập và kiểm thử các kịch bản phân mảnh mạng (network partition, split-brain), tái nhập cluster và đồng bộ trạng thái nhanh.
- **Chuẩn đầu ra (Learning Outcomes):**
  - Xây dựng tính năng Compact Log và InstallSnapshot RPC khi log đạt ngưỡng kích thước, lưu trạng thái snapshot an toàn xuống disk/memory.
  - Thiết lập testbed fault-injection mô phỏng rớt mạng đa chiều (majority vs minority partition), bảo đảm cluster chỉ chấp nhận ghi ở phân vùng đa số.
  - Đảm bảo tính nhất quán (linearizability) và tính toàn vẹn dữ liệu khi node bị cô lập gia nhập lại cluster và catch-up log.
- **Tiêu chí hoàn thành Milestone:** Chạy thành công kịch bản chaos test mô phỏng network partition: cụm từ chối ghi ở minority partition và duy trì ghi liên tục ở majority partition; sau khi hồi phục mạng, 100% dữ liệu trên 3 node đồng nhất tuyệt đối.
- **Khái niệm bổ sung (ngoài KB):** `raft-log-compaction-snapshotting`, `network-partition-handling`, `linearizable-consistency-model`, `chaos-fault-injection-testing`

#### M3. Giao diện Dịch vụ gRPC Streaming, Circuit Breaker & Retry Resiliency (540 phút | Phụ thuộc: M2)
- **Mô tả:** Xây dựng Protobuf schema cho KV Store service hỗ trợ Unary (Get, Put, Delete) và Server/Bidirectional Streaming (Watch Key events). Tích hợp gRPC Interceptors, triển khai pattern Circuit Breaker và Retry có Exponential Backoff cho Client-to-Cluster routing.
- **Chuẩn đầu ra (Learning Outcomes):**
  - Định nghĩa Protobuf v3 và sinh mã Go cho gRPC server/client hỗ trợ thao tác KV và streaming event khi key thay đổi.
  - Cài đặt gRPC Server Interceptor định tuyến request ghi về Leader node tự động hoặc phản hồi Leader hint cho client.
  - Áp dụng mẫu thiết kế Circuit Breaker và Retry exponential backoff với jitter nhằm ngăn chặn cascading failure khi cụm đang failover.
- **Tiêu chí hoàn thành Milestone:** Client gRPC tự động redirect request ghi về đúng Leader; endpoint Watch stream nhận được update ngay lập tức khi Put key thành công; Circuit Breaker ngắt kết nối chính xác khi node sập và tự phục hồi (half-open to closed) khi node sống lại.
- **Khái niệm bổ sung (ngoài KB):** `grpc-protobuf-streaming-api`, `grpc-unary-stream-interceptors`, `circuit-breaker-pattern`, `client-failover-routing`

#### M4. Quan sát Toàn diện với OpenTelemetry Tracing, Đóng gói Docker & Đo kiểm p99 Latency (540 phút | Phụ thuộc: M3)
- **Mô tả:** Tích hợp OpenTelemetry (OTel) SDK vào gRPC middleware và Raft pipeline để trace trọn vẹn vòng đời request từ client qua các node phân tán. Đóng gói cụm 3 node vào Docker Compose, chạy kịch bản tải bằng ghz/k6 và tối ưu p99 latency.
- **Chuẩn đầu ra (Learning Outcomes):**
  - Tích hợp OpenTelemetry Tracing với gRPC Metadata W3C Trace Context propagation, trực quan hóa span từ Client -> Leader -> Follower RPCs trên Jaeger/OTel Collector.
  - Thiết lập Docker Compose hoàn chỉnh gồm cụm 3-node KV Store, Jaeger UI, Prometheus/OTel Collector phục vụ kiểm thử end-to-end.
  - Tiến hành benchmark tải cao (read/write workload), phân tích CPU/Memory profile qua pprof để tìm điểm nghẽn và tối ưu hóa p99 latency dưới 20ms.
- **Tiêu chí hoàn thành Milestone:** Môi trường Docker Compose 3-node khởi động trơn tru; giao diện Jaeger hiển thị đầy đủ distributed trace tree cho cả write request qua Raft; báo cáo benchmark bằng ghz chứng minh throughput ổn định và p99 latency đạt mức tối ưu cam kết.
- **Khái niệm bổ sung (ngoài KB):** `opentelemetry-distributed-tracing`, `w3c-trace-context-propagation`, `docker-compose-multi-node-cluster`, `performance-benchmark-p99-latency`

---

## M-12 — Embedded Rust #![no_std] & RTOS Embassy cho Vi điều khiển ARM Cortex-M

### Thông tin mục tiêu & ràng buộc đầu vào

- **Trình độ người học:** `INTERMEDIATE`
- **Mô tả mục tiêu:** Làm chủ Rust #![no_std], Ownership/Lifetimes trên bộ nhớ tĩnh, HAL/PAC thanh ghi, DMA/SPI/I2C, Embassy async executor, RTIC interrupt scheduling và debug phần cứng bằng probe-rs/defmt trong 8 tuần.
- **Khung thời gian:** `2026-11-02` → `2026-12-28`
- **Quỹ thời gian rảnh:** MODE_B: monday 20:00–22:00, wednesday 20:00–22:00, saturday 14:00–17:00 | Ngày nghỉ: friday, sunday
- **Tóm tắt phạm vi lộ trình:** Lộ trình FULL_SCOPE 8 tuần bao phủ toàn bộ mục tiêu: lập trình Bare-metal Rust no_std trên ARM Cortex-M, làm chủ PAC/HAL, DMA zero-copy an toàn, async RTOS Embassy, mô hình định thời RTIC v2, và dự án tích hợp Telemetry Sensor Hub với công cụ debug chuyên sâu probe-rs/defmt.
- **Tổng quan Milestone Plan:** 7 milestones | Tổng effort: 3960 phút (66.0 giờ)

### Danh sách Milestones

#### M1. Thiết lập Toolchain & Môi trường Bare-metal Rust trên Cortex-M (420 phút | Phụ thuộc: Không)
- **Mô tả:** Cấu hình cross-compilation target thumbv7em-none-eabihf, linker script memory.x, panic-handler, defmt logging qua RTT và nạp firmware trực tiếp bằng probe-rs trên phần cứng STM32F4/RP2040.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M1-O1: Cấu hình Cargo.toml, target triple cortex-m và linker script memory.x cho vi điều khiển mục tiêu.
  - M1-O2: Khởi tạo chương trình bare-metal với thuộc tính #![no_std] và #[panic_handler] tùy biến.
  - M1-O3: Sử dụng defmt kết hợp probe-rs-run để truyền log debug qua RTT không phụ thuộc UART.
- **Tiêu chí hoàn thành Milestone:** Biên dịch thành công binary minimal #![no_std], nạp vào vi điều khiển qua probe-rs và xuất log defmt thời gian thực qua giao tiếp SWD.
- **Khái niệm bổ sung (ngoài KB):** `cortex-m-rt`, `no_std-panic-handling`, `probe-rs-rtt`, `defmt-logging`

#### M2. Mô hình Bộ nhớ Tĩnh, Thanh ghi PAC & Abstraction HAL (540 phút | Phụ thuộc: M1)
- **Mô tả:** Làm chủ mô hình quyền sở hữu đối với thanh ghi phần cứng (svd2rust PAC singleton pattern), nguyên lý mượn (borrowing) bộ nhớ tĩnh qua critical-section và xây dựng driver ngoại vi GPIO/UART cơ bản.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M2-O1: Giải thích cơ chế Peripherals::take() để đảm bảo an toàn truy cập thanh ghi PAC theo mô hình Ownership.
  - M2-O2: Quản lý biến tĩnh có thể thay đổi (static mut) an toàn bằng critical-section và RefCell.
  - M2-O3: Sử dụng traits từ embedded-hal để trừu tượng hóa ngoại vi GPIO và UART trên vi điều khiển.
- **Tiêu chí hoàn thành Milestone:** Viết driver điều khiển GPIO LED nhấp nháy và UART echo giao tiếp với PC ở tầng HAL không sử dụng unsafe ngoài các khối bao đóng trừu tượng chuẩn.
- **Khái niệm bổ sung (ngoài KB):** `pac-singleton-pattern`, `critical-section-synchronization`, `embedded-hal-traits`

#### M3. Giao tiếp SPI, I2C & Quản lý Bộ đệm DMA Zero-Copy An Toàn (660 phút | Phụ thuộc: M2)
- **Mô tả:** Triển khai giao thức ngoại vi SPI/I2C đọc dữ liệu cảm biến và thiết kế cơ chế chuyển giao bộ đệm DMA circular/ping-pong an toàn, triệt tiêu race condition mà không cần heap allocation.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M3-O1: Đọc và ghi thanh ghi cảm biến qua bus SPI/I2C bằng cấu trúc embedded-hal blocking.
  - M3-O2: Thiết lập luồng truyền nhận DMA bảo đảm ownership của bộ đệm tĩnh (static buffer borrowing) trong suốt thời gian giao dịch.
  - M3-O3: Xử lý sự kiện ngắt DMA Transfer Complete và kiểm tra dữ liệu bằng logic analyzer.
- **Tiêu chí hoàn thành Milestone:** Firmware đọc mẫu cảm biến liên tục qua SPI vào bộ đệm circular DMA, không xảy ra aliasing hay memory leak, xác thực qua logic analyzer.
- **Khái niệm bổ sung (ngoài KB):** `embedded-hal-spi-i2c`, `zero-copy-dma-ownership`, `circular-buffer-static`

#### M4. Lập trình Bất đồng bộ với Embassy Executor & Timers (600 phút | Phụ thuộc: M3)
- **Mô tả:** Nghiên cứu kiến trúc async/await trong embedded Rust, cách hoạt động của Embassy task scheduler (cooperative cooperative multitasking), wakers và timers không block CPU.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M4-O1: Định nghĩa và spawn các Embassy tasks độc lập với macro #[embassy_executor::task].
  - M4-O2: Ứng dụng Timer và Ticker của Embassy để định thời các chu kỳ task với độ trễ thấp.
  - M4-O3: Giải thích cơ chế Waker và cách Embassy executor chuyển trạng thái task từ Wait sang Ready qua sự kiện phần cứng.
- **Tiêu chí hoàn thành Milestone:** Chạy đồng thời ít nhất 3 task Embassy (nhấp nháy heartbeat, quét nút nhấn với debounce, định thời 100ms) trên vi điều khiển mà CPU ở chế độ WFI khi rảnh rỗi.
- **Khái niệm bổ sung (ngoài KB):** `embassy-executor`, `async-embedded-waker`, `embassy-time`

#### M5. Giao tiếp Liên tác vụ (IPC) & Async DMA Ngoại vi trong Embassy (660 phút | Phụ thuộc: M4)
- **Mô tả:** Tích hợp ngoại vi async của Embassy (embassy-stm32 hoặc embassy-rp) kết hợp cơ chế Channel, Signal và Mutex để trao đổi thông tin liên tác vụ không dùng khóa chặn (lock-free / async wait).
- **Chuẩn đầu ra (Learning Outcomes):**
  - M5-O1: Sử dụng async SPI/UART DMA drivers có sẵn trong hệ sinh thái Embassy để truyền nhận I/O không blocking.
  - M5-O2: Triển khai luồng dữ liệu an toàn giữa các tasks bằng embassy_sync::channel::Channel và Signal.
  - M5-O3: Ngăn ngừa deadlock và race condition khi chia sẻ bus hoặc tài nguyên chung bằng embassy_sync::mutex::Mutex.
- **Tiêu chí hoàn thành Milestone:** Task thu thập SPI DMA gửi gói tin vào Channel, task xử lý nhận gói tin và stream dữ liệu telemetry qua async UART mà không làm gián đoạn chu kỳ lấy mẫu.
- **Khái niệm bổ sung (ngoài KB):** `embassy-sync-primitives`, `async-dma-peripherals`, `inter-task-communication`

#### M6. So sánh RTIC v2 (Real-Time Interrupt-driven Concurrency) & Đo Timing Jitter (480 phút | Phụ thuộc: M5)
- **Mô tả:** Tìm hiểu kiến trúc điều phối theo mức ưu tiên dựa trên phần cứng NVIC của RTIC v2, thiết kế ứng dụng theo mô hình SRP (Stack Resource Policy) và đo đạc timing jitter so với Embassy.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M6-O1: Cấu hình ứng dụng RTIC v2 với các tasks ràng buộc trực tiếp vào ngắt phần cứng NVIC và software tasks.
  - M6-O2: Ứng dụng mô hình tài nguyên chia sẻ không deadlock thông qua khóa ưu tiên tức thời (Immediate Priority Ceiling Protocol).
  - M6-O3: Đo lường độ trễ đáp ứng (interrupt latency) và jitter thực tế bằng chân GPIO kích hoạt quan sát trên logic analyzer/oscilloscope.
- **Tiêu chí hoàn thành Milestone:** Xây dựng một bản demo xử lý xung ngắt bằng RTIC v2, đo đạc độ trễ phản hồi < 2 micro-giây và lập bảng so sánh ưu/nhược điểm giữa RTIC và Embassy.
- **Khái niệm bổ sung (ngoài KB):** `rtic-v2-framework`, `stack-resource-policy-srp`, `interrupt-latency-profiling`

#### M7. Đồ án Tích hợp: Telemetry Sensor Hub với Embassy, Zero-Copy DMA & defmt (600 phút | Phụ thuộc: M6)
- **Mô tả:** Xây dựng hệ thống firmware hoàn chỉnh: thu thập dữ liệu cảm biến đa kênh qua SPI DMA, mã hóa gói tin telemetry, xử lý lỗi bus I/O và phát sóng qua UART không nghẽn, kiểm thử toàn diện trên board thực.
- **Chuẩn đầu ra (Learning Outcomes):**
  - M7-O1: Đóng gói kiến trúc firmware phân lớp: Hardware Abstraction, Communication Manager, Data Processing và Telemetry Streaming.
  - M7-O2: Triển khai cơ chế watchdog, khôi phục lỗi bus ngoại vi (SPI bus stall / DMA overrun) tự động trong môi trường no_std.
  - M7-O3: Đóng gói và đo kiểm timing, mức tiêu thụ RAM tĩnh (.bss/.data) và Flash (.text) trên phần cứng thực.
- **Tiêu chí hoàn thành Milestone:** Firmware Sensor Hub chạy liên tục không crash trong 1 giờ, stream telemetry 50Hz qua UART DMA với độ trễ ổn định, kiểm soát bộ nhớ RAM tĩnh dưới ngưỡng cho phép.
- **Khái niệm bổ sung (ngoài KB):** `firmware-architecture-embedded-rust`, `watchdog-fault-handling`, `memory-footprint-optimization`

---
