# FocusFlow — Hệ thống Lập kế hoạch & Thực thi Lộ trình Tự học Thích ứng Tích hợp AI

Đồ án Tốt nghiệp Đại học ngành Công nghệ Thông tin — Khoa CNTT, Trường Đại học Sư phạm Kỹ thuật TP.HCM (HCMUTE).

* **Sinh viên thực hiện:**
  * Vũ Toàn Thắng (Lead Architect / PM)
  * Phan Đình Duẩn (Senior BA / Quality Lead)
* **Giảng viên Hướng dẫn:** ThS. Vũ Đình Bảo

---

## 1. Cấu trúc Dự án (Project Structure)

```text
FocusFlow/
├── backend/          # Backend FastAPI (Python 3.12, Hexagonal Architecture, uv)
│   ├── src/          # Domain, Application, Infrastructure, Presentation
│   ├── pyproject.toml# Quản lý phụ thuộc với Astral uv
│   └── Dockerfile    # Multi-stage build với uv
│
├── frontend/         # Frontend Next.js 15 (React 19, TypeScript, Tailwind v4, pnpm)
│   ├── src/app/      # App Router (Pages & Layouts)
│   ├── package.json  # Quản lý phụ thuộc với pnpm
│   └── Dockerfile    # Multi-stage build với node:22-alpine
│
├── docs/             # Hồ sơ Thiết kế & Kỹ thuật chuẩn mực (ISO 29148, UML 2.5, arc42)
│   ├── requirements/ # Bài toán thực tế, Chân dung người dùng & 5 KPIs
│   ├── srs/          # Đặc tả yêu cầu phần mềm SRS v1.1
│   ├── uml/          # Sequence Diagrams & State Machines UML 2.5.1
│   ├── architecture/ # Thiết kế kiến trúc tổng thể & C4 Model
│   ├── database/     # DB Diagram, PostgreSQL 16 DDL & Từ điển dữ liệu
│   ├── decisions/    # Bộ 6 Architecture Decision Records (ADRs) chuẩn MADR
│   └── engineering/  # Báo cáo kiểm toán tính nhất quán chéo Milestone 2
│
├── docs_ute/         # Hồ sơ Báo cáo tiến độ tuần & Tài liệu môn học nộp GVHD (.docx, .xlsx, .md)
├── docker-compose.yml# Khởi chạy 5 dịch vụ (PostgreSQL 16, Redis 7, API, Celery, Next.js)
├── .env.example      # Biến môi trường mẫu
└── AGENTS.md         # Quy chuẩn công nghệ và triết lý kỹ thuật hệ thống
```

---

## 2. Khởi chạy Nhanh với Docker Compose (Quickstart)

```bash
# 1. Sao chép cấu hình môi trường
cp .env.example .env

# 2. Khởi động toàn bộ cụm dịch vụ
docker compose up -d

# 3. Truy cập các cổng dịch vụ:
# - Giao diện người dùng (Frontend): http://localhost:3000
# - Tài liệu Swagger API (Backend):   http://localhost:8000/docs
# - Kiểm tra Health Check API:       http://localhost:8000/api/health
```

