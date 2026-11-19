import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { signal } from '@angular/core';
import { FeaturesComponent } from './features.component';
import { AuthService } from '../../core/services/auth.service';

describe('FeaturesComponent', () => {
  let component: FeaturesComponent;
  let fixture: ComponentFixture<FeaturesComponent>;
  let router: Router;
  let authServiceMock: {
    isAuthenticated: ReturnType<typeof signal<boolean>>;
  };

  beforeEach(async () => {
    authServiceMock = {
      isAuthenticated: signal<boolean>(false),
    };

    await TestBed.configureTestingModule({
      imports: [FeaturesComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(FeaturesComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockImplementation(() => Promise.resolve(true));
    fixture.detectChanges();
  });

  it('should create and render Hero Section with SRS v1.3+ Architecture Index', () => {
    expect(component).toBeTruthy();
    const el = fixture.nativeElement as HTMLElement;

    expect(el.textContent).toContain('NĂNG LỰC NỀN TẢNG');
    expect(el.textContent).toContain('CHỈ SỐ KIẾN TRÚC');
    expect(el.textContent).toContain('Chuẩn Đặc Tả SRS v1.3+');
    expect(el.textContent).toContain('6 Phân hệ SRL • 4 Bounded Contexts');
  });

  it('should render all 6 real FocusFlow SRL subsystems in the Bento Grid', () => {
    const el = fixture.nativeElement as HTMLElement;

    // Module 01
    expect(el.textContent).toContain('01 / Lập Lộ Trình & RAG');
    expect(el.textContent).toContain('Khởi tạo Lộ trình Hybrid RAG & Pedagogy Grill-Me');
    expect(el.textContent).toContain('pgvector');
    expect(el.textContent).toContain('tsvector');
    expect(el.textContent).toContain('<untrusted_knowledge_context>');
    expect(el.textContent).toContain('FIT_CAPACITY');
    expect(el.querySelector('a[href="/how-it-works"]')).toBeTruthy();

    // Module 02
    expect(el.textContent).toContain('02 / Xếp Lịch Tất Định');
    expect(el.textContent).toContain('Lịch Mode A/B & Cổng Kiểm duyệt 3 Tầng');
    expect(el.textContent).toContain('3-Tier Gate');
    expect(el.textContent).toContain('Mode A/B • 0 AI Credit Re-optimize');

    // Module 03
    expect(el.textContent).toContain('03 / Study Workspace Studio');
    expect(el.textContent).toContain('Đồng hồ Timestamp-Delta, MVS & TakeawayGuard');
    expect(el.textContent).toContain('Pomodoro 25:00 | MVS 15:00 | Stopwatch');
    expect(el.textContent).toContain('Heartbeat 60s');
    expect(el.textContent).toContain('PARTIAL_COMPLETED');

    // Module 04
    expect(el.textContent).toContain('04 / Môi Trường Tập Trung');
    expect(el.textContent).toContain('Focus Shield, Sticky Notes & Web Audio Mixer');
    expect(el.textContent).toContain('Tiếng mưa • Brown Noise • Lò sưởi & Gió');
    expect(el.textContent).toContain('Tab Guard • Zen Lock • Parking Lot');

    // Module 05
    expect(el.textContent).toContain('05 / Phục Hồi Thích Ứng');
    expect(el.textContent).toContain('Domino Shift, Overdue Recovery & Cầu dao STALLED');
    expect(el.textContent).toContain('Domino Shift:');
    expect(el.textContent).toContain('+0 reschedule_count');
    expect(el.textContent).toContain('STALLED Circuit Breaker:');
    expect(el.textContent).toContain('Backlog Priority Ranker:');

    // Module 06
    expect(el.textContent).toContain('06 / Kiểm Chứng & Đánh Giá');
    expect(el.textContent).toContain('Prove Mode, Hồ sơ 4×3 & Weekly AI Review');
    expect(el.textContent).toContain('Giờ tập trung');
    expect(el.textContent).toContain('Task Completion');
    expect(el.textContent).toContain('Plan Adherence');
    expect(el.textContent).toContain('WRLS');
  });

  it('should default to thesis scenario and allow switching to certificate and language', () => {
    const el = fixture.nativeElement as HTMLElement;

    // Default is 'thesis'
    expect(component.activeDisciplineTab()).toBe('thesis');
    expect(component.currentDiscipline().tabLabel).toBe('Đồ án & Nghiên cứu CNTT');
    expect(el.textContent).toContain('Hybrid RAG • DAG • Prove Mode');
    expect(el.textContent).toContain('roadmap_feasibility.json');
    expect(el.textContent).toContain('"dag_cycles": 0');
    expect(el.textContent).toContain('Phê duyệt 2 Cấp độ & Feasibility Check');

    // Switch to 'certificate'
    component.setDiscipline('certificate');
    fixture.detectChanges();

    expect(component.activeDisciplineTab()).toBe('certificate');
    expect(component.currentDiscipline().tabLabel).toBe('Chứng chỉ & Người đi làm');
    expect(el.textContent).toContain('BUSY_PRO • FIT_CAPACITY • MVS');
    expect(el.textContent).toContain('workspace_session_spec.json');
    expect(el.textContent).toContain('"mvs_min_minutes": 10');
    expect(el.textContent).toContain('"heartbeat_sec": 60');
    expect(el.textContent).toContain('"takeaway_min_chars": 30');
    expect(el.textContent).toContain('Bảo Toàn Nhịp Học Không Áp Lực');

    // Switch to 'language'
    component.setDiscipline('language');
    fixture.detectChanges();

    expect(component.activeDisciplineTab()).toBe('language');
    expect(component.currentDiscipline().tabLabel).toBe('Ngoại ngữ & Tự học Dài hạn');
    expect(el.textContent).toContain('Focus Shield • Web Audio • Weekly Review');
    expect(el.textContent).toContain('weekly_review_summary.json');
    expect(el.textContent).toContain('"learner_model": "4x3 (EXPLICIT/OBSERVED/INFERRED)"');
    expect(el.textContent).toContain('"wrls_recovered_sessions": "tracked"');
    expect(el.textContent).toContain('Khép Kín Chu Trình Zimmerman SRL');
  });

  it('should navigate unauthenticated users to sign-up on getStarted()', () => {
    authServiceMock.isAuthenticated.set(false);

    component.getStarted();
    expect(router.navigate).toHaveBeenCalledWith(['/sign-up']);
  });

  it('should navigate authenticated users to roadmaps on getStarted()', () => {
    authServiceMock.isAuthenticated.set(true);

    component.getStarted();
    expect(router.navigate).toHaveBeenCalledWith(['/roadmaps']);
  });

  it('should render Zimmerman SRL spotlight, pricing CTA, and zero fabricated Stitch strings', () => {
    const el = fixture.nativeElement as HTMLElement;
    const text = el.textContent ?? '';

    // Zimmerman SRL Spotlight
    expect(text).toContain('Barry J. Zimmerman (2002)');
    expect(text).toContain('Mô hình Self-Regulated Learning (SRL) — Nền tảng lý thuyết của FocusFlow');

    // Bottom CTA
    expect(text).toContain('Sẵn sàng xây dựng lộ trình tự học có kiểm soát và thích ứng theo nhịp sống thực?');
    expect(text).toContain('30 lượt điều phối AI miễn phí mỗi tháng');
    expect(text).toContain('Bắt đầu miễn phí');
    expect(text).toContain('Xem bảng giá gói');
    expect(el.querySelector('a[href="/pricing"]')).toBeTruthy();

    // Ensure no fabricated Stitch template data remains
    expect(text).not.toContain('Elena Rostova');
    expect(text).not.toContain('ETH Zürich');
    expect(text).not.toContain('CognitiveBlock');
    expect(text).not.toContain('focusflow sync');
    expect(text).not.toContain('1.240 Thẻ');
    expect(text).not.toContain('STAMINA INDEX');
    expect(text).not.toContain('Kyoto Temple Rainfall');
    expect(text).not.toContain('Bodleian Library Whisper');
    expect(text).not.toContain('6 Unified Cognitive Modules');
  });
});
