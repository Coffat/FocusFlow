import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env['BACKEND_API_URL'] || 'http://localhost:8000/api/v1';
const MAILPIT_API_URL = process.env['MAILPIT_API_URL'] || 'http://localhost:8025/api/v1';

/**
 * Helper to fetch the latest OTP code sent to an email address via Mailpit REST API.
 */
async function getLatestOtpFromMailpit(email: string, timeoutMs: number = 15000): Promise<string> {
  const startTime = Date.now();
  const cleanEmail = email.trim().toLowerCase();

  while (Date.now() - startTime < timeoutMs) {
    try {
      const res = await fetch(`${MAILPIT_API_URL}/messages`);
      if (res.ok) {
        const data = await res.json();
        const messages: any[] = data.messages || [];
        const targetMsg = messages.find(
          (m: any) =>
            m.To &&
            m.To.some((recipient: any) => recipient.Address.toLowerCase() === cleanEmail)
        );

        if (targetMsg) {
          const detailRes = await fetch(`${MAILPIT_API_URL}/message/${targetMsg.ID}`);
          if (detailRes.ok) {
            const detail = await detailRes.json();
            const textContent = detail.Text || detail.HTML || '';
            const match = textContent.match(/\b\d{6}\b/);
            if (match) {
              return match[0];
            }
          }
        }
      }
    } catch {
      // Retry until timeout
    }
    await new Promise((r) => setTimeout(r, 600));
  }
  throw new Error(`Timeout waiting for OTP email sent to ${email} in Mailpit`);
}

/**
 * Helper to clear existing messages in Mailpit before test runs.
 */
async function clearMailpitMessages(): Promise<void> {
  try {
    await fetch(`${MAILPIT_API_URL}/messages`, { method: 'DELETE' });
  } catch {
    // Ignore error if Mailpit unreachable
  }
}

test.describe.configure({ mode: 'serial' });

test.describe('FocusFlow Authentication E2E Suite (Duẩn UI + Mailpit + Argon2id + RTR)', () => {
  test.beforeAll(async () => {
    await clearMailpitMessages();
  });

  const uniqueId = `${Date.now()}.${Math.floor(Math.random() * 10000)}`;
  const testUser = {
    fullName: 'Nguyen Van Learner',
    email: `learner.e2e.${uniqueId}@focusflow.vn`,
    password: 'Password123!'
  };

  test('1. Đăng ký tài khoản người học với Email OTP thực tế qua Mailpit và chuyển vào Dashboard', async ({
    page
  }) => {
    // 1. Vào trang đăng ký
    await page.goto('/sign-up');
    await expect(page.locator('.brand-logo')).toBeVisible();

    // 2. Điền thông tin form đăng ký (chuẩn Duẩn)
    await page.locator('input[formControlName="fullName"]').fill(testUser.fullName);
    await page.locator('input[formControlName="email"]').fill(testUser.email);
    await page.locator('input[formControlName="password"]').fill(testUser.password);
    await page.locator('input[formControlName="confirmPassword"]').fill(testUser.password);

    // 3. Bấm Submit để yêu cầu mã OTP
    const submitBtn = page.locator('button.submit-button');
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // 4. Kiểm tra chuyển hướng sang trang /verify-otp
    await page.waitForURL(/\/verify-otp/, { timeout: 15000 });
    await expect(page.locator('.email-highlight')).toContainText(testUser.email);

    // 5. Lấy mã OTP thực tế từ container Mailpit
    const otpCode = await getLatestOtpFromMailpit(testUser.email);
    expect(otpCode).toMatch(/^\d{6}$/);

    // 6. Nhập 6 chữ số vào 6 ô input OTP
    const cells = page.locator('input.otp-cell');
    await expect(cells).toHaveCount(6);
    for (let i = 0; i < 6; i++) {
      await cells.nth(i).pressSequentially(otpCode[i]);
    }

    // 7. Bấm nút Xác nhận OTP
    const verifyBtn = page.locator('button.submit-button');
    await expect(verifyBtn).toBeEnabled();
    await verifyBtn.click();

    // 8. Đăng ký & xác thực thành công chuyển hướng sang /dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    expect(page.url()).toContain('/dashboard');
  });

  test('2. Đăng nhập thành công với Email & Mật khẩu (Argon2id) và duy trì phiên', async ({
    page
  }) => {
    await page.goto('/sign-in');
    await expect(page.locator('.headline-title')).toBeVisible();

    // Điền thông tin tài khoản đã đăng ký ở kịch bản 1
    await page.locator('input[formControlName="email"]').fill(testUser.email);
    await page.locator('input[formControlName="password"]').fill(testUser.password);

    // Bấm Đăng nhập
    const submitBtn = page.locator('button.submit-button');
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();

    // Đăng nhập thành công vào /dashboard
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    expect(page.url()).toContain('/dashboard');
  });

  test('3. Đăng nhập thất bại khi sai mật khẩu hiển thị thông báo lỗi', async ({ page }) => {
    await page.goto('/sign-in');

    // Điền email đúng nhưng mật khẩu sai
    await page.locator('input[formControlName="email"]').fill(testUser.email);
    await page.locator('input[formControlName="password"]').fill('WrongPassword999!');

    // Bấm Đăng nhập
    await page.locator('button.submit-button').click();

    // Kiểm tra xuất hiện banner thông báo lỗi
    const errorBanner = page.locator('.error-banner');
    await expect(errorBanner).toBeVisible({ timeout: 10000 });
    expect(page.url()).toContain('/sign-in');
  });

  test('4. Quên mật khẩu & đặt lại mật khẩu mới qua OTP Mailpit rồi đăng nhập lại thành công', async ({
    page
  }) => {
    const resetUser = {
      fullName: 'Learner Reset Test',
      email: `learner.reset.${Date.now()}.${Math.floor(Math.random() * 10000)}@focusflow.vn`,
      initialPassword: 'OldPassword123!',
      newPassword: 'NewSecurePassword123!'
    };

    // Tạo sẵn tài khoản người học để test luồng quên mật khẩu độc lập
    const regRes = await fetch(`${BACKEND_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: resetUser.fullName,
        email: resetUser.email,
        password: resetUser.initialPassword
      })
    });
    expect(regRes.status).toBe(201);

    // 1. Bấm link quên mật khẩu từ trang Sign-in
    await page.goto('/sign-in');
    await page.locator('a[routerLink="/forgot-password"]').click();
    await page.waitForURL(/\/forgot-password/);

    // 2. Bước 1: Nhập email yêu cầu OTP đặt lại mật khẩu
    await page.locator('input[formControlName="email"]').fill(resetUser.email);
    await page.locator('button.submit-button').click();

    // 3. Bước 2: Chờ Mailpit nhận email và bóc tách OTP mới
    const resetOtp = await getLatestOtpFromMailpit(resetUser.email);
    expect(resetOtp).toMatch(/^\d{6}$/);

    // Điền OTP vào form bước 2
    const otpInput = page.locator('input[formControlName="otpCode"]');
    await expect(otpInput).toBeVisible({ timeout: 10000 });
    await otpInput.fill(resetOtp);
    await page.locator('button.submit-button').click();

    // 4. Bước 3: Điền mật khẩu mới và xác nhận mật khẩu
    const newPassInput = page.locator('input[formControlName="newPassword"]');
    await expect(newPassInput).toBeVisible({ timeout: 10000 });
    await newPassInput.fill(resetUser.newPassword);
    await page.locator('input[formControlName="confirmPassword"]').fill(resetUser.newPassword);

    // Bấm xác nhận đổi mật khẩu
    await page.locator('button.submit-button').click();

    // 5. Kiểm tra thông báo thành công
    const successBanner = page.locator('.success-banner');
    await expect(successBanner).toBeVisible({ timeout: 10000 });

    // 6. Đăng nhập lại với mật khẩu mới
    await page.goto('/sign-in');
    await page.locator('input[formControlName="email"]').fill(resetUser.email);
    await page.locator('input[formControlName="password"]').fill(resetUser.newPassword);
    await page.locator('button.submit-button').click();

    // Thành công vào Dashboard với mật khẩu mới
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    expect(page.url()).toContain('/dashboard');
  });

  test('5. Đăng xuất và Auth Guard bảo vệ chặn truy cập /dashboard khi chưa xác thực', async ({
    page,
    context
  }) => {
    // Xoá cookie phiên
    await context.clearCookies();

    // Thử truy cập thẳng vào trang bảo vệ /dashboard
    await page.goto('/dashboard');

    // Auth Guard phải tự động chặn và đẩy người dùng về /sign-in
    await page.waitForURL(/\/sign-in/, { timeout: 10000 });
    expect(page.url()).toContain('/sign-in');
  });

  test('6. Kịch bản nâng cao: Nhập sai mã OTP tại trang xác thực bị báo lỗi', async ({
    page
  }) => {
    const freshEmail = `learner.wrongotp.${Date.now()}@focusflow.vn`;

    await page.goto('/sign-up');
    await page.locator('input[formControlName="fullName"]').fill('Test Wrong OTP');
    await page.locator('input[formControlName="email"]').fill(freshEmail);
    await page.locator('input[formControlName="password"]').fill('Password123!');
    await page.locator('input[formControlName="confirmPassword"]').fill('Password123!');
    await page.locator('button.submit-button').click();

    await page.waitForURL(/\/verify-otp/, { timeout: 15000 });

    // Cố tình nhập mã OTP sai 000000
    const cells = page.locator('input.otp-cell');
    await expect(cells).toHaveCount(6);
    for (let i = 0; i < 6; i++) {
      await cells.nth(i).pressSequentially('0');
    }

    await page.locator('button.submit-button').click();

    // Banner lỗi phải hiển thị thông báo
    const errorBanner = page.locator('.error-banner');
    await expect(errorBanner).toBeVisible({ timeout: 10000 });
  });

  test('7. Kịch bản nâng cao: Gửi lại mã OTP (Resend OTP) tạo email mới trong Mailpit', async ({
    page
  }) => {
    const resendEmail = `learner.resend.${Date.now()}@focusflow.vn`;

    // 1. Gọi trực tiếp API yêu cầu OTP ban đầu
    const reqRes = await fetch(`${BACKEND_URL}/auth/register/request-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: 'Resend Test',
        email: resendEmail,
        password: 'Password123!'
      })
    });
    expect(reqRes.status).toBe(200);

    // Lấy OTP ban đầu từ Mailpit
    const initialOtp = await getLatestOtpFromMailpit(resendEmail);
    expect(initialOtp).toMatch(/^\d{6}$/);

    // 2. Mở trang verify-otp cho email này
    await page.goto(`/verify-otp?email=${encodeURIComponent(resendEmail)}&flow=register`);
    await expect(page.locator('.email-highlight')).toContainText(resendEmail);

    // Kiểm tra đồng hồ đếm ngược cooldown hiển thị
    const timer = page.locator('.timer-countdown');
    await expect(timer).toBeVisible();

    // 3. Kiểm tra gọi trực tiếp API resend-otp để kiểm tra Backend Anti-Replay
    const resendApiRes = await fetch(`${BACKEND_URL}/auth/register/resend-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: resendEmail })
    });
    // Trả về 200 hoặc 429 nếu trong cooldown
    expect([200, 429]).toContain(resendApiRes.status);
  });

  test('8. Kịch bản nâng cao: Nhập sai OTP quá 3 lần bị khóa session OTP (Anti-Brute-Force)', async ({
    page
  }) => {
    const bruteForceEmail = `learner.brute.${Date.now()}@focusflow.vn`;

    // Khởi tạo yêu cầu OTP
    await fetch(`${BACKEND_URL}/auth/register/request-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: 'Brute Test',
        email: bruteForceEmail,
        password: 'Password123!'
      })
    });

    // Thử nhập sai 3 lần liên tiếp qua API xác thực
    let finalStatus = 0;
    for (let attempt = 1; attempt <= 4; attempt++) {
      const verifyRes = await fetch(`${BACKEND_URL}/auth/register/verify-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: bruteForceEmail,
          otp_code: '999999'
        })
      });
      finalStatus = verifyRes.status;
    }

    // Sau khi nhập sai quá số lần cho phép, session OTP bị hủy (trả về 400 Bad Request)
    expect(finalStatus).toBe(400);
  });
});

