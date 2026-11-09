import { ChangeDetectionStrategy, Component, model } from '@angular/core';

export type WorkspaceTab = 'dag' | 'schedule' | 'pomodoro';

@Component({
  selector: 'app-interactive-workspace',
  standalone: true,
  templateUrl: './interactive-workspace.component.html',
  styleUrl: './interactive-workspace.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InteractiveWorkspaceComponent {
  readonly activeTab = model<WorkspaceTab>('dag');

  setTab(tab: WorkspaceTab): void {
    this.activeTab.set(tab);
  }

  scrollTo(elementId: string, event?: Event): void {
    if (event) {
      event.preventDefault();
    }
    const element = document.getElementById(elementId);
    if (element && typeof element.scrollIntoView === 'function') {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
}
