import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_ENDPOINTS } from '../constants/api-endpoints';
import type { components } from '../api/schema';

export type BillingConfigResponseDTO = components['schemas']['BillingConfigResponseDTO'];
export type BillingPlanDTO = components['schemas']['BillingPlanDTO'];
export type BillingWebhookResponseDTO = components['schemas']['BillingWebhookResponseDTO'];
export type CreateCheckoutRequestDTO = components['schemas']['CreateCheckoutRequestDTO'];
export type CheckoutResponseDTO = components['schemas']['CheckoutResponseDTO'];
export type PaymentTransactionDTO = components['schemas']['PaymentTransactionDTO'];

@Injectable({
  providedIn: 'root',
})
export class BillingService {
  private readonly http = inject(HttpClient);

  getBillingConfig(): Observable<BillingConfigResponseDTO> {
    return this.http.get<BillingConfigResponseDTO>(API_ENDPOINTS.ACCOUNT_BILLING.CONFIG, {
      withCredentials: true,
    });
  }

  createCheckout(
    planCode: CreateCheckoutRequestDTO['plan_code'],
  ): Observable<CheckoutResponseDTO> {
    const body: CreateCheckoutRequestDTO = { plan_code: planCode };
    return this.http.post<CheckoutResponseDTO>(API_ENDPOINTS.ACCOUNT_BILLING.CHECKOUT, body, {
      withCredentials: true,
    });
  }

  listTransactions(): Observable<PaymentTransactionDTO[]> {
    return this.http.get<PaymentTransactionDTO[]>(API_ENDPOINTS.ACCOUNT_BILLING.TRANSACTIONS, {
      withCredentials: true,
    });
  }

  confirmMockCheckout(transactionId: string): Observable<BillingWebhookResponseDTO> {
    return this.http.post<BillingWebhookResponseDTO>(
      API_ENDPOINTS.ACCOUNT_BILLING.MOCK_CONFIRM(transactionId),
      {},
      { withCredentials: true },
    );
  }
}
