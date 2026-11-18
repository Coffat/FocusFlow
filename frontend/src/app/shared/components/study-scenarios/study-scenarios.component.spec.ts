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

  it('should initialize with thesis scenario', () => {
    expect(component).toBeTruthy();
    expect(component.activeScenario()).toBe('thesis');
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Khóa luận Tốt nghiệp CNTT');
    expect(el.textContent).toContain('SRS & Đặc tả Kiến trúc');
  });

  it('should switch to aws and ai scenarios when setScenario is called', async () => {
    component.setScenario('aws');
    fixture.detectChanges();
    await fixture.whenStable();

    let el = fixture.nativeElement as HTMLElement;
    expect(component.activeScenario()).toBe('aws');
    expect(el.textContent).toContain('Chinh phục chứng chỉ AWS SAA-C03');
    expect(el.textContent).toContain('IAM, VPC & Mạng Đám Mây Toàn Diện');

    component.setScenario('ai');
    fixture.detectChanges();
    await fixture.whenStable();

    el = fixture.nativeElement as HTMLElement;
    expect(component.activeScenario()).toBe('ai');
    expect(el.textContent).toContain('Chuyển dịch năng lực AI Engineer');
    expect(el.textContent).toContain('Fine-tuning Llama/Qwen');
  });
});
