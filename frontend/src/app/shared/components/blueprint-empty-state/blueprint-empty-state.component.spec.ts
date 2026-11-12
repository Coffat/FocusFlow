import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import {
  BlueprintEmptyStateComponent,
  StarterTemplate,
} from './blueprint-empty-state.component';

describe('BlueprintEmptyStateComponent', () => {
  let component: BlueprintEmptyStateComponent;
  let fixture: ComponentFixture<BlueprintEmptyStateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BlueprintEmptyStateComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(BlueprintEmptyStateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('khởi tạo thành công BlueprintEmptyStateComponent', () => {
    expect(component).toBeTruthy();
  });

  it('hiển thị tiêu đề, mô tả và SVG blueprint bản thảo', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Chưa có lộ trình học tập nào');
    expect(el.querySelector('svg')).toBeTruthy();
  });

  it('hiển thị 3 starter templates mặc định', () => {
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('FastAPI & Microservices');
    expect(el.textContent).toContain('AWS Solutions Architect');
    expect(el.textContent).toContain('IELTS Academic Band 7.5');
  });

  it('phát sự kiện selectTemplate khi chọn một mẫu lộ trình', () => {
    const spy = vi.fn();
    component.selectTemplate.subscribe(spy);

    const testTpl: StarterTemplate = {
      id: 'custom-tpl',
      title: 'Data Science & MLOps',
      subtitle: 'Xây dựng pipeline ML',
      categoryTag: 'Data',
      weeksCount: 6,
      tasksCount: 40,
      tags: ['Data', 'MLOps'],
    };

    component.onSelectTemplate(testTpl);
    expect(spy).toHaveBeenCalledWith(testTpl);
  });

  it('phát sự kiện createCustomRoadmap khi click tạo mới thủ công', () => {
    const spy = vi.fn();
    component.createCustomRoadmap.subscribe(spy);

    component.onCreateCustom();
    expect(spy).toHaveBeenCalled();
  });
});
