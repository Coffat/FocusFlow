import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_ENDPOINTS } from '../../../core/constants/api-endpoints';
import type { operations } from '../../../core/api/schema';

export type AdminStatusResponseDTO =
  operations['get_admin_status_api_v1_account_admin_status_get']['responses']['200']['content']['application/json'];

@Injectable({
  providedIn: 'root',
})
export class AdminStatusService {
  private readonly http = inject(HttpClient);

  getStatus(): Observable<AdminStatusResponseDTO> {
    return this.http.get<AdminStatusResponseDTO>(API_ENDPOINTS.SETTINGS.ADMIN_STATUS, {
      withCredentials: true,
    });
  }
}
