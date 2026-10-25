# Angular 21+ Patterns — FocusFlow

## Directory Structure

```
frontend/src/app/
  core/
    constants/       # App-wide constants
    guards/          # Route guards (auth, role)
    interceptors/    # HTTP interceptors (auth token, error handling)
    models/          # Shared TypeScript interfaces
    services/        # Singleton services (auth, user, etc.)
  features/
    {feature-name}/
      {name}.component.ts
      {name}.component.html
      {name}.component.scss
      {name}.component.spec.ts
      {name}.service.ts         # Feature-specific service (if needed)
  shared/
    components/      # Reusable UI components
    pipes/           # Custom pipes
    directives/      # Custom directives
```

## Standalone Component Template

```typescript
// features/tasks/task-list.component.ts
import { Component, OnInit, inject, DestroyRef } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';
import { TaskService } from './task.service';
import { Task } from '../../core/models/task.model';

@Component({
  selector: 'app-task-list',
  standalone: true,
  imports: [CommonModule, ButtonModule, TableModule],
  templateUrl: './task-list.component.html',
  styleUrl: './task-list.component.scss',
})
export class TaskListComponent implements OnInit {
  destroyRef = inject(DestroyRef);
  taskService = inject(TaskService);

  tasks: Task[] = [];
  loading = false;

  ngOnInit() {
    this.loadTasks();
  }

  loadTasks() {
    this.loading = true;
    this.taskService
      .getTasks()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.tasks = data;
          this.loading = false;
        },
        error: (err) => {
          console.error('Failed to load tasks', err);
          this.loading = false;
        },
        complete: () => {},
      });
  }
}
```

## Service Template

```typescript
// features/tasks/task.service.ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Task } from '../../core/models/task.model';

@Injectable({ providedIn: 'root' })
export class TaskService {
  http = inject(HttpClient);
  BASE_URL = '/api/v1/tasks';

  getTasks(): Observable<Task[]> {
    return this.http.get<Task[]>(this.BASE_URL);
  }

  createTask(task: Partial<Task>): Observable<Task> {
    return this.http.post<Task>(this.BASE_URL, task);
  }

  updateTask(id: string, task: Partial<Task>): Observable<Task> {
    return this.http.put<Task>(`${this.BASE_URL}/${id}`, task);
  }

  deleteTask(id: string): Observable<void> {
    return this.http.delete<void>(`${this.BASE_URL}/${id}`);
  }
}
```

## SCSS Template

```scss
// features/tasks/task-list.component.scss
:host {
  display: block;
}

.task-list-container {
  padding: 1.5rem;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

// — Responsive —
@media (max-width: 768px) {
  .task-list-container {
    padding: 0.75rem;
  }

  .task-header {
    flex-direction: column;
    gap: 0.5rem;
  }
}

// — PrimeNG Overrides —
::ng-deep {
  .p-datatable .p-datatable-tbody > tr > td {
    color: var(--on-surface);
  }
}
```

## Routing — Lazy Load

```typescript
// app.routes.ts
export const routes: Routes = [
  {
    path: 'tasks',
    loadComponent: () =>
      import('./features/tasks/task-list.component').then(
        (m) => m.TaskListComponent
      ),
    canActivate: [authGuard],
  },
];
```

## Test Template

```typescript
// features/tasks/task-list.component.spec.ts
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { TaskListComponent } from './task-list.component';
import { TaskService } from './task.service';
import { of } from 'rxjs';

describe('TaskListComponent', () => {
  let component: TaskListComponent;
  let fixture: ComponentFixture<TaskListComponent>;
  let mockService: jasmine.SpyObj<TaskService>;

  beforeEach(async () => {
    mockService = jasmine.createSpyObj('TaskService', ['getTasks']);
    mockService.getTasks.and.returnValue(of([]));

    await TestBed.configureTestingModule({
      imports: [TaskListComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TaskService, useValue: mockService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(TaskListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should load tasks on init', () => {
    expect(mockService.getTasks).toHaveBeenCalled();
  });
});
```
