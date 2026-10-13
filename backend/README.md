# FocusFlow Backend

Hệ thống Backend FastAPI cho FocusFlow, xây dựng theo chuẩn Kiến trúc Lục giác (Hexagonal Architecture / Ports & Adapters) với Python 3.12, SQLAlchemy 2.0 Async, Celery và Redis.

## Quản lý môi trường với `uv`
```bash
# Cài đặt dependencies
uv sync

# Chạy server phát triển (Development server)
uv run uvicorn src.presentation.main:app --reload --port 8000

# Chạy kiểm thử (Tests)
uv run pytest
```
