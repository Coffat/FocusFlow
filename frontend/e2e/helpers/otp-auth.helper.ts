import { APIRequestContext, APIResponse } from '@playwright/test';

export const DEFAULT_BACKEND_API_URL =
  process.env['BACKEND_API_URL'] || 'http://127.0.0.1:3000/api/v1';

export const DEFAULT_MAILPIT_API_URL =
  process.env['MAILPIT_API_URL'] || 'http://127.0.0.1:8025/api/v1';

export const E2E_TRUSTED_ORIGIN = new URL(
  process.env['PLAYWRIGHT_BASE_URL'] || 'http://127.0.0.1:3000'
).origin;

export const E2E_CSRF_HEADERS: Readonly<Record<string, string>> = {
  Origin: E2E_TRUSTED_ORIGIN,
};

interface MailpitRecipient {
  Address: string;
}

interface MailpitMessageSummary {
  ID: string;
  To?: MailpitRecipient[];
}

interface MailpitMessagesResponse {
  messages?: MailpitMessageSummary[];
}

interface MailpitMessageDetail {
  Text?: string;
  HTML?: string;
}

export interface MailpitOtpOptions {
  mailpitApiUrl?: string;
  timeoutMs?: number;
  excludeMessageIds?: ReadonlySet<string>;
  deleteAfterRead?: boolean;
}

export interface RegisterWithOtpParams {
  fullName: string;
  email: string;
  password: string;
  backendApiUrl?: string;
  mailpitApiUrl?: string;
  requestTimeoutMs?: number;
  otpTimeoutMs?: number;
}

/**
 * Polls Mailpit REST API for the latest 6-digit OTP email sent to `email`.
 * Optionally deletes the matched message by ID after reading so subsequent
 * OTP flows for the same email (e.g., forgot-password) never collide with it.
 */
export async function getLatestOtpFromMailpit(
  email: string,
  options: MailpitOtpOptions = {}
): Promise<string> {
  const mailpitApiUrl = options.mailpitApiUrl ?? DEFAULT_MAILPIT_API_URL;
  const timeoutMs = options.timeoutMs ?? 15000;
  const excludeMessageIds = options.excludeMessageIds;
  const deleteAfterRead = options.deleteAfterRead ?? false;

  const startTime = Date.now();
  const cleanEmail = email.trim().toLowerCase();

  while (Date.now() - startTime < timeoutMs) {
    try {
      const res = await fetch(`${mailpitApiUrl}/messages?limit=100`);
      if (res.ok) {
        const data = (await res.json()) as MailpitMessagesResponse;
        const messages = data.messages ?? [];
        const targetMsg = messages.find(
          (m) =>
            (!excludeMessageIds || !excludeMessageIds.has(m.ID)) &&
            Array.isArray(m.To) &&
            m.To.some((recipient) => recipient.Address.toLowerCase() === cleanEmail)
        );

        if (targetMsg) {
          const detailRes = await fetch(`${mailpitApiUrl}/message/${targetMsg.ID}`);
          if (detailRes.ok) {
            const detail = (await detailRes.json()) as MailpitMessageDetail;
            const textContent = detail.Text || detail.HTML || '';
            const match = textContent.match(/\b\d{6}\b/);
            if (match) {
              if (deleteAfterRead) {
                await fetch(`${mailpitApiUrl}/messages`, {
                  method: 'DELETE',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ IDs: [targetMsg.ID] }),
                }).catch(() => undefined);
              }
              return match[0];
            }
          }
        }
      }
    } catch {
      // Retry until timeout
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }

  throw new Error(`Timeout waiting for OTP email sent to ${email} in Mailpit (${mailpitApiUrl})`);
}

/**
 * Registers a fresh user via the real 2-step Email OTP flow:
 * 1. POST /auth/register/request-otp
 * 2. Poll Mailpit for the 6-digit OTP email sent to `email`
 * 3. POST /auth/register/verify-otp (populates HttpOnly auth cookies on `request`)
 */
export async function registerUserWithOtp(
  request: APIRequestContext,
  params: RegisterWithOtpParams
): Promise<APIResponse> {
  const backendApiUrl = params.backendApiUrl ?? DEFAULT_BACKEND_API_URL;
  const mailpitApiUrl = params.mailpitApiUrl ?? DEFAULT_MAILPIT_API_URL;

  const reqRes = await request.post(`${backendApiUrl}/auth/register/request-otp`, {
    data: {
      full_name: params.fullName,
      email: params.email,
      password: params.password,
    },
    ...(params.requestTimeoutMs ? { timeout: params.requestTimeoutMs } : {}),
  });

  if (!reqRes.ok()) {
    return reqRes;
  }

  const otpCode = await getLatestOtpFromMailpit(params.email, {
    mailpitApiUrl,
    timeoutMs: params.otpTimeoutMs ?? 15000,
    deleteAfterRead: true,
  });

  return request.post(`${backendApiUrl}/auth/register/verify-otp`, {
    headers: E2E_CSRF_HEADERS,
    data: {
      email: params.email,
      otp_code: otpCode,
    },
    ...(params.requestTimeoutMs ? { timeout: params.requestTimeoutMs } : {}),
  });
}
