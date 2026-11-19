import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { signal } from '@angular/core';
import { FaqComponent } from './faq.component';
import { AuthService } from '../../core/services/auth.service';

describe('FaqComponent', () => {
  let component: FaqComponent;
  let fixture: ComponentFixture<FaqComponent>;
  let router: Router;
  let authServiceMock: {
    isAuthenticated: ReturnType<typeof signal<boolean>>;
  };

  beforeEach(async () => {
    authServiceMock = {
      isAuthenticated: signal<boolean>(false),
    };

    await TestBed.configureTestingModule({
      imports: [FaqComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(FaqComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockImplementation(() => Promise.resolve(true));
    fixture.detectChanges();
  });

  it('should create and render default state with 10 questions across 4 categories', () => {
    expect(component).toBeTruthy();
    expect(component.searchQuery()).toBe('');
    expect(component.selectedCategory()).toBe('all');
    expect(component.faqCategories.length).toBe(4);
    expect(component.totalMatchingQuestions()).toBe(10);

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Mọi Điều Bạn Cần Biết Về FocusFlow.');
    expect(el.textContent).toContain('FocusFlow khác biệt như thế nào so với Notion hay Google Calendar thông thường?');
  });

  it('should filter questions by category tab', () => {
    component.selectCategory('engine');
    fixture.detectChanges();

    expect(component.selectedCategory()).toBe('engine');
    expect(component.filteredFaqCategories().length).toBe(1);
    expect(component.filteredFaqCategories()[0].id).toBe('engine');
    expect(component.totalMatchingQuestions()).toBe(4);

    component.selectCategory('pedagogy');
    fixture.detectChanges();

    expect(component.filteredFaqCategories().length).toBe(1);
    expect(component.filteredFaqCategories()[0].id).toBe('pedagogy');
    expect(component.totalMatchingQuestions()).toBe(3);

    component.selectCategory('all');
    fixture.detectChanges();

    expect(component.filteredFaqCategories().length).toBe(4);
    expect(component.totalMatchingQuestions()).toBe(10);
  });

  it('should filter questions realtime by search query and auto-open matching questions', () => {
    component.updateSearchQuery('Domino Shift');
    fixture.detectChanges();

    expect(component.totalMatchingQuestions()).toBeGreaterThanOrEqual(1);
    const matching = component.filteredFaqCategories();
    expect(matching.some((c) => c.questions.some((q) => q.question.includes('Domino Shift')))).toBe(true);

    // Auto-open should be true when search query is present
    expect(component.isQuestionOpen('q2')).toBe(true);

    component.clearSearch();
    fixture.detectChanges();

    expect(component.searchQuery()).toBe('');
    expect(component.totalMatchingQuestions()).toBe(10);
  });

  it('should show empty state when search finds no results', () => {
    component.updateSearchQuery('không-thể-tìm-thấy-từ-này-123456');
    fixture.detectChanges();

    expect(component.filteredFaqCategories().length).toBe(0);
    expect(component.totalMatchingQuestions()).toBe(0);

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Không tìm thấy câu hỏi phù hợp');
  });

  it('should toggle accordion questions', () => {
    expect(component.isQuestionOpen('q1')).toBe(true);

    component.toggleQuestion('q1');
    expect(component.isQuestionOpen('q1')).toBe(false);

    component.toggleQuestion('q2');
    expect(component.isQuestionOpen('q2')).toBe(true);
  });

  it('should focus search input when Cmd+K or Ctrl+K is pressed', () => {
    const focusSpy = vi.fn();
    if (component.searchInputElement) {
      component.searchInputElement.nativeElement.focus = focusSpy;
    }

    const event = new KeyboardEvent('keydown', { key: 'k', metaKey: true });
    window.dispatchEvent(event);

    expect(focusSpy).toHaveBeenCalled();
  });

  it('should navigate on startFreeJourney according to auth status', () => {
    authServiceMock.isAuthenticated.set(false);
    component.startFreeJourney();
    expect(router.navigate).toHaveBeenCalledWith(['/sign-up']);

    authServiceMock.isAuthenticated.set(true);
    component.startFreeJourney();
    expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
  });
});
