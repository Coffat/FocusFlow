import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { GOOGLE_CLIENT_ID } from '../../constant/api.constant';

export interface GoogleCredentialResponse {
  credential: string;
  select_by: string;
}

export interface GoogleTokenResponse {
  access_token: string;
  expires_in: number;
  scope: string;
  token_type: string;
  error: string;
}

export interface GoogleTokenClient {
  requestAccessToken: () => void;
}

export interface GoogleIdAccounts {
  initialize: (options: { client_id: string; callback: (response: GoogleCredentialResponse) => void }) => void;
  prompt: () => void;
  renderButton: (element: HTMLElement, options: Record<string, string>) => void;
}

export interface GoogleOAuth2 {
  initTokenClient: (options: { client_id: string; scope: string; callback: (response: GoogleTokenResponse) => void }) => GoogleTokenClient;
}

export interface GoogleGlobal {
  accounts: {
    id: GoogleIdAccounts;
    oauth2: GoogleOAuth2;
  };
}

declare global {
  interface Window {
    google: GoogleGlobal;
  }
}

@Injectable({
  providedIn: 'root'
})
export class GoogleSsoService {
  credentialSubject = new Subject<string>();
  credential$ = this.credentialSubject.asObservable();

  tokenSubject = new Subject<string>();
  token$ = this.tokenSubject.asObservable();

  errorSubject = new Subject<string>();
  error$ = this.errorSubject.asObservable();

  tokenClient: GoogleTokenClient = {
    requestAccessToken: () => {}
  };
  hasTokenClient = false;
  isInitialized = false;

  hasGoogleSdk(): boolean {
    return Boolean('google' in window && window.google && window.google.accounts);
  }

  getGoogle(): GoogleGlobal {
    return window.google;
  }

  initialize() {
    if (!this.hasGoogleSdk()) {
      return;
    }

    try {
      const google = this.getGoogle();

      google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (response: GoogleCredentialResponse) => {
          if (response.credential.length > 0) {
            this.credentialSubject.next(response.credential);
          }
        }
      });

      this.tokenClient = google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: 'email profile openid',
        callback: (response: GoogleTokenResponse) => {
          if (response.access_token.length > 0) {
            this.tokenSubject.next(response.access_token);
          } else if (response.error.length > 0) {
            this.errorSubject.next(response.error);
          }
        }
      });

      this.hasTokenClient = true;
      this.isInitialized = true;
    } catch (err) {
      const errorMsg = (err as Error).message || 'Google SSO initialization error';
      this.errorSubject.next(errorMsg);
    }
  }

  requestGoogleSignIn() {
    if (!this.isInitialized) {
      this.initialize();
    }

    if (this.hasTokenClient) {
      this.tokenClient.requestAccessToken();
      return;
    }

    if (this.hasGoogleSdk()) {
      const google = this.getGoogle();
      google.accounts.id.prompt();
    } else {
      this.errorSubject.next('Google Identity Services SDK is not loaded.');
    }
  }
}
