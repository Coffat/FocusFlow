# FocusFlow Frontend

Ứng dụng Frontend cho FocusFlow, xây dựng với **Angular 21** (Standalone Components, Signals, Zoneless, Control Flow `@if`/`@for`), **PrimeNG**, **Tailwind CSS**, **SCSS**, quản lý gói bằng **`pnpm`**.

## Hướng dẫn cài đặt & Chạy ứng dụng

```bash
# 1. Cài đặt dependencies
pnpm install

# 2. Chạy server phát triển (Development server)
pnpm start
# hoặc
pnpm dev

# 3. Build ứng dụng sản xuất (Production bundle)
pnpm build

# 4. Chạy kiểm thử đơn vị (Unit Tests với Vitest)
pnpm test
```

## Các lệnh kiểm tra chất lượng

```bash
# Lint code
pnpm lint

# Unit tests
pnpm test

# Generate API TypeScript types từ OpenAPI
pnpm api:gen
```
