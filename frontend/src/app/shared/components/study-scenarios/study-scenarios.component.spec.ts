import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StudyScenariosComponent } from './study-scenarios.component';

describe('StudyScenariosComponent', () => {
  let component: StudyScenariosComponent;
  let fixture: ComponentFixture<StudyScenariosComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [StudyScenariosComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(StudyScenariosComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should initialize with thesis scenario and domain attributes', () => {
    expect(component).toBeTruthy();
    expect(component.activeScenario()).toBe('thesis');

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Khóa luận Tốt nghiệp CNTT');
    expect(el.textContent).toContain('Mode B: T2–T6 (19:30–21:30) • T7 (09:00–11:30)');
    expect(el.textContent).toContain('72 giờ');
    expect(el.textContent).toContain('Khả thi • Tải 78% quỹ giờ rảnh');
    expect(el.textContent).toContain('SRS & ADR Specs');
    expect(el.textContent).toContain('SRS & Đặc tả Kiến trúc');
    expect(el.textContent).toContain('24 giờ • 16 blocks');
    expect(el.textContent).toContain('Prove Mode: Phản biện đặc tả SRS & ERD');
    expect(el.textContent).toContain('Phân rã Use Case & Ràng buộc nghiệp vụ');
  });

  it('should switch to aws and ai scenarios when setScenario is called', async () => {
    component.setScenario('aws');
    fixture.detectChanges();
    await fixture.whenStable();

    let el = fixture.nativeElement as HTMLElement;
    expect(component.activeScenario()).toBe('aws');
    expect(el.textContent).toContain('Chinh phục chứng chỉ AWS SAA-C03');
    expect(el.textContent).toContain('40 giờ');
    expect(el.textContent).toContain('AWS SAA-C03 Exam Guide');
    expect(el.textContent).toContain('IAM, VPC & Mạng Đám Mây Toàn Diện');
    expect(el.textContent).toContain('Prove Mode: Lab thiết kế VPC Multi-AZ');

    component.setScenario('ai');
    fixture.detectChanges();
    await fixture.whenStable();

    el = fixture.nativeElement as HTMLElement;
    expect(component.activeScenario()).toBe('ai');
    expect(el.textContent).toContain('Chuyển dịch năng lực AI Engineer');
    expect(el.textContent).toContain('96 giờ');
    expect(el.textContent).toContain('arXiv RAG Surveys');
    expect(el.textContent).toContain('Fine-tuning Llama/Qwen & Production Serving');
    expect(el.textContent).toContain('Prove Mode: Golden Eval 0 Regression');
  });
});
