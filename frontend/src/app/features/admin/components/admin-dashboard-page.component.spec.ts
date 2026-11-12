import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AdminDashboardPageComponent } from './admin-dashboard-page.component';

describe('AdminDashboardPageComponent', () => {
  let component: AdminDashboardPageComponent;
  let fixture: ComponentFixture<AdminDashboardPageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminDashboardPageComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(AdminDashboardPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('khởi tạo thành công trang admin dashboard', () => {
    expect(component).toBeTruthy();
  });

  it('hiển thị empty state khi danh sách người học rỗng', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Chưa có người học nào trong danh sách quản trị');
  });

  it('hiển thị danh sách người học và cấp phát thêm AI quota thành công', () => {
    component.users.set([
      {
        id: 'usr-01',
        email: 'test@focusflow.edu.vn',
        role: 'LEARNER',
        tier: 'PRO',
        status: 'ACTIVE',
        remainingCredits: 10,
      },
    ]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('test@focusflow.edu.vn');
    expect(el.textContent).toContain('10 lượt');

    component.grantBonusQuota('usr-01');
    fixture.detectChanges();

    expect(el.textContent).toContain('15 lượt');
  });
});
