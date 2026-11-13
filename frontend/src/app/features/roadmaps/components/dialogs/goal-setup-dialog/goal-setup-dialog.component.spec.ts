import { ComponentFixture, TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { GoalSetupDialogComponent } from './goal-setup-dialog.component';

describe('GoalSetupDialogComponent', () => {
  let component: GoalSetupDialogComponent;
  let fixture: ComponentFixture<GoalSetupDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [GoalSetupDialogComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(GoalSetupDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('hiển thị lỗi kiểm tra khi bấm Tiếp tục mà chưa nhập mục tiêu học tập', () => {
    const submitSpy = vi.fn();
    component.submitGoal.subscribe(submitSpy);

    const compiled = fixture.nativeElement as HTMLElement;
    const submitBtn = compiled.querySelector('[data-testid="goal-submit-btn"]') as HTMLButtonElement;
    submitBtn.click();
    fixture.detectChanges();

    expect(submitSpy).not.toHaveBeenCalled();
    const errorEl = compiled.querySelector('[data-testid="goal-validation-error"]');
    expect(errorEl).toBeTruthy();
  });

  it('điền nhanh mục tiêu khi bấm vào Quick Suggestion Chip và cập nhật ước tính AI', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const chip0 = compiled.querySelector('[data-testid="goal-suggestion-chip-0"]') as HTMLButtonElement;
    expect(chip0).toBeTruthy();
    chip0.click();
    fixture.detectChanges();

    expect(component.goalTitle()).toBe('Chứng chỉ AWS Solutions Architect');
    const estimateBox = compiled.querySelector('[data-testid="ai-cognitive-estimate-box"]');
    expect(estimateBox?.textContent).toContain('giờ học');
    expect(estimateBox?.textContent).toContain('phiên Pomodoro');
  });

  it('phát sự kiện submitGoal với đầy đủ thông tin khi hợp lệ', () => {
    const submitSpy = vi.fn();
    component.submitGoal.subscribe(submitSpy);

    component.selectSuggestion('Luyện thi IELTS 7.5 Academic');
    component.selectLevel('INTERMEDIATE');
    component.onWeeklyHoursChange(15);
    fixture.detectChanges();

    component.onSubmit();

    expect(submitSpy).toHaveBeenCalledTimes(1);
    const payload = submitSpy.mock.calls[0][0];
    expect(payload.title).toBe('Luyện thi IELTS 7.5 Academic');
    expect(payload.prior_knowledge_level).toBe('INTERMEDIATE');
  });

  it('cho phép đính kèm đường dẫn URL hợp lệ và tệp .pdf hợp lệ, đồng thời hiển thị chip tài liệu', () => {
    component.toggleUrlInput();
    component.onUrlInputChange('https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html');
    component.addUrlAttachment();

    const pdfFile = new File(['dummy pdf content'], 'aws-study-guide.pdf', {
      type: 'application/pdf',
    });
    component.addFiles([pdfFile]);
    fixture.detectChanges();

    expect(component.attachments().length).toBe(2);
    expect(component.attachments()[0].kind).toBe('URL');
    expect(component.attachments()[1].kind).toBe('FILE');
    expect(component.attachments()[1].title).toBe('aws-study-guide.pdf');

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('[data-testid="goal-attachment-chip-0"]')).toBeTruthy();
    expect(compiled.querySelector('[data-testid="goal-attachment-chip-1"]')).toBeTruthy();
  });

  it('giới hạn tối đa 3 nguồn đính kèm (tệp + URL) để bảo vệ ngữ cảnh AI', () => {
    const file1 = new File(['# Notes 1'], 'note-1.md', { type: 'text/markdown' });
    const file2 = new File(['Notes 2'], 'note-2.txt', { type: 'text/plain' });
    component.addFiles([file1, file2]);

    component.onUrlInputChange('https://roadmap.sh/aws');
    component.addUrlAttachment();
    expect(component.attachments().length).toBe(3);
    expect(component.isAttachmentLimitReached()).toBe(true);

    // Thử thêm nguồn thứ 4
    component.onUrlInputChange('https://aws.amazon.com/certification/');
    component.addUrlAttachment();
    fixture.detectChanges();

    expect(component.attachments().length).toBe(3);
    const compiled = fixture.nativeElement as HTMLElement;
    const errEl = compiled.querySelector('[data-testid="goal-attachment-error"]');
    expect(errEl).toBeTruthy();
    expect(errEl?.textContent).toContain('tối đa 3 nguồn');
  });

  it('từ chối tệp vượt quá 5 MB hoặc định dạng không hỗ trợ (.exe)', () => {
    const invalidExtFile = new File(['binary'], 'installer.exe', {
      type: 'application/octet-stream',
    });
    component.addFiles([invalidExtFile]);
    fixture.detectChanges();

    expect(component.attachments().length).toBe(0);
    expect(component.attachmentError()).toContain('.pdf, .md hoặc .txt');

    const oversizedBuffer = new Uint8Array(5 * 1024 * 1024 + 1024);
    const oversizedFile = new File([oversizedBuffer], 'huge-book.pdf', {
      type: 'application/pdf',
    });
    component.addFiles([oversizedFile]);
    fixture.detectChanges();

    expect(component.attachments().length).toBe(0);
    const compiled = fixture.nativeElement as HTMLElement;
    const errEl = compiled.querySelector('[data-testid="goal-attachment-error"]');
    expect(errEl).toBeTruthy();
    expect(errEl?.textContent).toContain('5 MB');
  });
});
