# FocusFlow — Hướng Dẫn Cấu Hình và Vận Hành Model Context Protocol (MCP)

Tài liệu này chuẩn hóa và ghi nhận kiến trúc tích hợp các MCP Server trong dự án **FocusFlow** nhằm hỗ trợ quy trình phát triển pair programming, kiểm thử tự động, tra cứu tài liệu và truy vấn cơ sở dữ liệu an toàn.

---

## 1. Tổng Quan Kiến Trúc MCP Servers

Hệ thống MCP được cấu hình tại [.agents/mcp_config.json](file:///Users/vuthang/Documents/FocusFlow/.agents/mcp_config.json) (đã được đưa vào [.gitignore](file:///Users/vuthang/Documents/FocusFlow/.gitignore) để bảo vệ credential) và file mẫu [.agents/mcp_config.example.json](file:///Users/vuthang/Documents/FocusFlow/.agents/mcp_config.example.json) để chia sẻ trong nhóm phát triển.

Bảng tổng hợp 4 MCP Server chính:

| Tên Server | Giao thức / Runner | Package / Image | Vai trò trong FocusFlow | Ghi chú kỹ thuật & Tối ưu |
| :--- | :--- | :--- | :--- | :--- |
| **`context7`** | `npx` (Node.js) | `@upstash/context7-mcp@latest` | Cung cấp ngữ cảnh tài liệu mới nhất từ các thư viện mã nguồn mở, framework (FastAPI, Next.js 15, Tailwind v4, v.v.) | Chạy stdio mặc định, cờ `-y` tự động xác nhận npx. Không bắt buộc API key cho truy vấn cơ bản. |
| **`github`** | `docker` | `ghcr.io/github/github-mcp-server` | Tương tác trực tiếp với GitHub Repository ([Coffat/FocusFlow](https://github.com/Coffat/FocusFlow)): issues, pull requests, commit status | Truyền biến môi trường `GITHUB_PERSONAL_ACCESS_TOKEN`. **Yêu cầu Docker Desktop phải đang chạy**. |
| **`postgres`** | `uvx` (Python) | `postgres-mcp` | Kiểm tra cấu trúc schema, bảng, chỉ mục và dữ liệu phân tích của PostgreSQL | **Bắt buộc cờ `--with "mcp<2"`** để tránh lỗi xung đột `FastMCP` trên thư viện `mcp` 2.x. Chạy ở chế độ `--access-mode=restricted` (chỉ đọc). |
| **`playwright`**| `npx` (Node.js) | `@playwright/mcp@latest` | Kiểm thử giao diện tự động (E2E), kiểm tra UI/UX, hỗ trợ skill `verify-ui` | Thêm cờ `-y` để tránh treo tiến trình ngầm; giữ chế độ Headed mở trình duyệt thực tế để lập trình viên quan sát. |

---

## 2. Chi Tiết Cấu Hình `.agents/mcp_config.json`

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": [
        "-y",
        "@upstash/context7-mcp@latest"
      ]
    },
    "github": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
      }
    },
    "postgres": {
      "command": "uvx",
      "args": [
        "--with",
        "mcp<2",
        "postgres-mcp",
        "--access-mode=restricted"
      ],
      "env": {
        "DATABASE_URI": "postgresql://focusflow_ro:${FOCUSFLOW_DB_PASSWORD:-<MAT_KHAU>}@localhost:5432/focusflow_db"
      }
    },
    "playwright": {
      "command": "npx",
      "args": [
        "-y",
        "@playwright/mcp@latest"
      ]
    }
  }
}
```

---

## 3. Hướng Dẫn Thiết Lập & Tiền Điều Kiện

### 3.1. Thiết Lập Biến Môi Trường GitHub Token
Tạo Fine-grained Personal Access Token trên GitHub:
1. Truy cập `GitHub Settings > Developer Settings > Personal access tokens > Fine-grained tokens`.
2. Giới hạn Resource Owner: tài khoản của bạn, Repository access: chỉ chọn repository **`Coffat/FocusFlow`**.
3. Cấp quyền tối thiểu: `Issues` (Read & Write), `Pull requests` (Read & Write), `Contents` (Read-only).
4. Thêm biến môi trường vào file cấu hình shell (`~/.zshrc`) hoặc file `.env`:
   ```bash
   export GITHUB_PERSONAL_ACCESS_TOKEN="github_pat_xxxx..."
   ```
5. Đảm bảo ứng dụng **Docker Desktop** đã được khởi chạy trên macOS trước khi gọi các công cụ GitHub MCP.

---

### 3.2. Thiết Lập User Read-Only Cho PostgreSQL (`focusflow_ro`)
Tuân thủ nguyên tắc đặc quyền tối thiểu (Principle of Least Privilege), MCP Server chỉ được phép đọc dữ liệu (chế độ `restricted`), không được phép chạy các lệnh phá hủy schema (`DROP`, `DELETE`, `TRUNCATE`).

Khi cơ sở dữ liệu `focusflow_db` được khởi chạy (qua Docker Compose hoặc Postgres local), thực thi đoạn SQL sau bằng user quản trị (`postgres`):

```sql
-- 1. Tạo user read-only cho MCP
CREATE USER focusflow_ro WITH PASSWORD 'MatKhauBaoMatCuaBan123!';

-- 2. Cấp quyền kết nối vào database
GRANT CONNECT ON DATABASE focusflow_db TO focusflow_ro;

-- 3. Cấp quyền xem schema public
\c focusflow_db
GRANT USAGE ON SCHEMA public TO focusflow_ro;

-- 4. Cấp quyền SELECT trên toàn bộ các bảng hiện có
GRANT SELECT ON ALL TABLES IN SCHEMA public TO focusflow_ro;

-- 5. Đảm bảo các bảng tạo mới trong tương lai cũng được cấp quyền SELECT tự động
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO focusflow_ro;
```

Sau đó, xuất biến môi trường hoặc cập nhật trực tiếp mật khẩu vào [.agents/mcp_config.json](file:///Users/vuthang/Documents/FocusFlow/.agents/mcp_config.json):
```bash
export FOCUSFLOW_DB_PASSWORD="MatKhauBaoMatCuaBan123!"
```

---

### 3.3. Kiểm Thử Độc Lập Các MCP Server Bằng CLI

Nếu cần xác minh tính tương thích của từng MCP Server ngoài môi trường IDE:

* **Kiểm tra Context7**:
  ```bash
  npx -y @upstash/context7-mcp@latest --help
  ```

* **Kiểm tra Playwright MCP**:
  ```bash
  npx -y @playwright/mcp@latest --version
  ```

* **Kiểm tra Postgres MCP** (lưu ý cờ `--with "mcp<2"`):
  ```bash
  uvx --with "mcp<2" postgres-mcp --help
  ```

* **Kiểm tra GitHub MCP** (yêu cầu Docker Desktop đang chạy):
  ```bash
  docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server --help
  ```
