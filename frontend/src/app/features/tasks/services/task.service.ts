import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { BacklogTask } from '../models/task.model';

@Injectable({
  providedIn: 'root'
})
export class TaskService {
  private readonly http = inject(HttpClient);

  readonly tasks = signal<BacklogTask[]>([]);

  updateTaskStatus(taskId: string, status: BacklogTask['status']): void {
    this.tasks.update((list) =>
      list.map((t) => (t.id === taskId ? { ...t, status } : t))
    );
  }
}
