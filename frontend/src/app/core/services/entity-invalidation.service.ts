import { Injectable, Signal, WritableSignal, signal } from '@angular/core';
import { components } from '../api/schema';

export type EntityDomain =
  | 'roadmaps'
  | 'tasks'
  | 'schedule'
  | 'dashboard'
  | 'workspace'
  | 'analytics'
  | 'availability';

export type TaskResponse = components['schemas']['TaskResponse'];

const ALL_DOMAINS: readonly EntityDomain[] = [
  'roadmaps',
  'tasks',
  'schedule',
  'dashboard',
  'workspace',
  'analytics',
  'availability',
] as const;

@Injectable({
  providedIn: 'root',
})
export class EntityInvalidationService {
  private readonly versions: Record<EntityDomain, WritableSignal<number>> = {
    roadmaps: signal<number>(0),
    tasks: signal<number>(0),
    schedule: signal<number>(0),
    dashboard: signal<number>(0),
    workspace: signal<number>(0),
    analytics: signal<number>(0),
    availability: signal<number>(0),
  };

  private readonly readonlyVersions: Record<EntityDomain, Signal<number>> = {
    roadmaps: this.versions.roadmaps.asReadonly(),
    tasks: this.versions.tasks.asReadonly(),
    schedule: this.versions.schedule.asReadonly(),
    dashboard: this.versions.dashboard.asReadonly(),
    workspace: this.versions.workspace.asReadonly(),
    analytics: this.versions.analytics.asReadonly(),
    availability: this.versions.availability.asReadonly(),
  };

  private readonly _lastTaskMutation = signal<TaskResponse | null>(null);
  readonly lastTaskMutation = this._lastTaskMutation.asReadonly();

  versionFor(domain: EntityDomain): Signal<number> {
    return this.readonlyVersions[domain];
  }

  invalidate(...domains: EntityDomain[]): void {
    for (const domain of new Set(domains)) {
      this.versions[domain].update((v) => v + 1);
    }
  }

  notifyTaskMutated(task: TaskResponse): void {
    this._lastTaskMutation.set({ ...task });
  }

  resetForTests(): void {
    for (const domain of ALL_DOMAINS) {
      this.versions[domain].set(0);
    }
    this._lastTaskMutation.set(null);
  }
}
