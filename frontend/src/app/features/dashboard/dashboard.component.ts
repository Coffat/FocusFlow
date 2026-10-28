import { Component, OnInit, DestroyRef, inject } from '@angular/core';
import { Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ButtonModule } from 'primeng/button';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/services/translation.service';
import { TranslatePipe } from '../../shared/pipes/translate.pipe';
import { UserProfile } from '../../models/auth.interface';

@Component({
  selector: 'app-dashboard',
  imports: [ButtonModule, TranslatePipe],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss'
})
export class DashboardComponent implements OnInit {
  authService: AuthService;
  translationService: TranslationService;
  router: Router;
  destroyRef: DestroyRef;

  currentUser: UserProfile = {
    id: '',
    email: '',
    fullName: '',
    role: '',
    tier: '',
    createdAt: ''
  };

  constructor(
    authService: AuthService,
    translationService: TranslationService,
    router: Router
  ) {
    this.authService = authService;
    this.translationService = translationService;
    this.router = router;
    this.destroyRef = inject(DestroyRef);
  }

  ngOnInit() {
    this.authService.currentUser$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (user: UserProfile) => {
          if (user && user.email) {
            this.currentUser = user;
          }
        },
        error: (_err: Error) => {},
        complete: () => {}
      });

    if (!this.currentUser.email) {
      this.authService.initAuth();
    }
  }

  signOut() {
    this.authService.signOut();
    this.router.navigate(['/sign-in']);
  }
}
