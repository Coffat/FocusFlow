import Link from "next/link";
import { Sparkles, Calendar, BookOpen, Clock, ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <main className="max-w-5xl mx-auto px-4 py-16">
      {/* Hero Header */}
      <div className="text-center space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
          <Sparkles className="w-4 h-4" />
          <span>FocusFlow v1.0 — Đồ án Tốt nghiệp CNTT HCMUTE</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900">
          Hệ thống Lập kế hoạch & Thực thi <br />
          <span className="text-indigo-600">Lộ trình Tự học Thích ứng</span>
        </h1>
        <p className="max-w-2xl mx-auto text-lg text-slate-600">
          Tự động hóa phân rã lộ trình bằng Google Gemini API với Cổng Duyệt Con người (Human-in-the-Loop), 
          không gian học tập trung Pomodoro và cơ chế thích ứng dời lịch tất định Domino Shift.
        </p>
      </div>

      {/* Feature Cards Grid */}
      <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="p-6 bg-white rounded-xl shadow-sm border border-slate-200 hover:shadow-md transition">
          <div className="w-12 h-12 flex items-center justify-center rounded-lg bg-indigo-100 text-indigo-600 mb-4">
            <Sparkles className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">1. AI Phân rã 2 Chặng</h2>
          <p className="mt-2 text-slate-600 text-sm">
            Duyệt Cột mốc vĩ mô (Milestones) trước khi AI sinh danh sách nhiệm vụ chi tiết và xếp lịch tự động.
          </p>
        </div>

        <div className="p-6 bg-white rounded-xl shadow-sm border border-slate-200 hover:shadow-md transition">
          <div className="w-12 h-12 flex items-center justify-center rounded-lg bg-emerald-100 text-emerald-600 mb-4">
            <Clock className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">2. Không gian Học tập trung</h2>
          <p className="mt-2 text-slate-600 text-sm">
            Tích hợp đồng hồ Pomodoro, Checklist nhiệm vụ, ghi chép nhanh và gửi nhịp tim đồng bộ an toàn qua Redis Buffer.
          </p>
        </div>

        <div className="p-6 bg-white rounded-xl shadow-sm border border-slate-200 hover:shadow-md transition">
          <div className="w-12 h-12 flex items-center justify-center rounded-lg bg-amber-100 text-amber-600 mb-4">
            <Calendar className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">3. Thích ứng Domino Shift</h2>
          <p className="mt-2 text-slate-600 text-sm">
            Tịnh tiến lịch trình thông minh khi người học bận việc đột xuất; tự động đồng bộ 1 chiều qua Apple/Google Calendar WebCal.
          </p>
        </div>
      </div>

      {/* Architecture Badge */}
      <div className="mt-16 p-6 bg-slate-900 text-white rounded-2xl flex flex-col md:flex-row items-center justify-between gap-6">
        <div>
          <h3 className="text-lg font-bold">Kiến trúc Hệ thống Chuẩn hóa Hexagonal & Next.js 15</h3>
          <p className="text-sm text-slate-400 mt-1">
            Backend FastAPI (Python 3.12, Celery, Redis, PostgreSQL 16) • Frontend Next.js 15 (React 19, Tailwind v4)
          </p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition"
          >
            <span>Swagger API Docs</span>
            <ArrowRight className="w-4 h-4" />
          </a>
        </div>
      </div>
    </main>
  );
}
