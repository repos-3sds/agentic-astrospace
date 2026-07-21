import { expect, test, type Page, type TestInfo } from '@playwright/test';

const mockKundlis = [
  {
    id: 'profile-1',
    name: 'Anika Rao',
    relation: 'Self',
    sun_sign: 'Leo',
    moon_sign: 'Cancer',
    ascendant: 'Libra',
    birth_year: 1992,
    birth_month: 8,
    birth_day: 12,
    birth_hour: 9,
    birth_minute: 30,
    birth_city: 'Mumbai',
    birth_nation: 'IN',
  },
];

const mockCalendarIntelligence = {
  start_date: '2026-07-21',
  by_date: {
    '2026-07-21': [],
  },
  current: {
    active_rules: [],
    strongest_transit: null,
    panchanga: {
      nakshatra: 'Rohini',
    },
    dasha: {
      mahadasha: { lord: 'Venus' },
      antardasha: { lord: 'Moon' },
    },
  },
};

async function mockApi(page: Page): Promise<void> {
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url());

    if (url.pathname === '/api/v1/auth/config') {
      await route.fulfill({ json: { enabled: false } });
      return;
    }

    if (url.pathname === '/api/v1/kundlis') {
      await route.fulfill({ json: mockKundlis });
      return;
    }

    if (url.pathname.includes('/calendar-intelligence')) {
      await route.fulfill({ json: mockCalendarIntelligence });
      return;
    }

    await route.fulfill({ status: 500, json: { detail: 'Not mocked in mobile shell test' } });
  });
}

async function expectNoHorizontalOverflow(page: Page): Promise<void> {
  const overflow = await page.evaluate(() => {
    const root = document.documentElement;
    return {
      clientWidth: root.clientWidth,
      scrollWidth: root.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
    };
  });

  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
  expect(overflow.bodyScrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
}

function skipUnlessPhone(testInfo: TestInfo): void {
  test.skip(!testInfo.project.name.startsWith('mobile-'), 'Phone-only shell assertion');
}

function skipOnPhone(testInfo: TestInfo): void {
  test.skip(testInfo.project.name.startsWith('mobile-'), 'Tablet/desktop-only shell assertion');
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
});

test.describe('phone shell', () => {
  test('uses app bar and bottom navigation without page overflow', async ({ page }, testInfo) => {
    skipUnlessPhone(testInfo);
    await page.goto('/app');

    await expect(page.getByRole('navigation', { name: 'Primary navigation' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Choose kundli profile' })).toBeVisible();
    await expect(page.locator('app-sidebar')).toBeHidden();

    await expect(page.getByRole('button', { name: 'Home' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    await expect(page.getByRole('button', { name: 'Profiles' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Ask AI' })).toBeVisible();
    await expect(
      page.getByRole('navigation', { name: 'Primary navigation' }).getByRole('button', {
        name: 'Settings',
      }),
    ).toBeVisible();
    await expect(page.getByRole('button', { name: 'More', exact: true })).toBeVisible();

    await expectNoHorizontalOverflow(page);
  });

  test('More sheet exposes specialist modules and account actions', async ({ page }, testInfo) => {
    skipUnlessPhone(testInfo);
    await page.goto('/kundli/profile-1/notes');
    await page.getByRole('button', { name: 'More', exact: true }).click();

    const dialog = page.getByRole('dialog', { name: 'More navigation' });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Edit Details' })).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Vedic Details', exact: true })).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Varga Charts', exact: true })).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Calendar & Panchanga', exact: true })).toBeVisible();
    await expect(dialog.getByRole('button', { name: /Settings/ })).toBeVisible();
    await expect(dialog.getByRole('button', { name: /Logout/ })).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
    await expectNoHorizontalOverflow(page);
  });

  test('profile sheet supports search and profile selection', async ({ page }, testInfo) => {
    skipUnlessPhone(testInfo);
    await page.goto('/app');
    await page.getByRole('button', { name: 'Choose kundli profile' }).click();

    const dialog = page.getByRole('dialog', { name: 'Choose profile' });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText('Anika Rao')).toBeVisible();

    await dialog.getByPlaceholder('Search name, sign, city, relation...').fill('mumbai');
    await expect(dialog.getByText('Anika Rao')).toBeVisible();
    await expect(dialog.getByText(/Self.*Leo.*Mumbai/)).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
  });

  test('profile workspace uses story tabs and one-tap Home', async ({ page }, testInfo) => {
    skipUnlessPhone(testInfo);
    await page.goto('/kundli/profile-1/overview');

    await expect(page.getByRole('button', { name: 'Back to home' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Today' })).toHaveAttribute('aria-current', 'page');
    await expect(page.getByRole('button', { name: 'Chart' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Timeline' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Ask' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'More', exact: true })).toBeVisible();

    await page.getByRole('button', { name: 'Back to home' }).click();
    await expect(page).toHaveURL(/\/app$/);
  });

  test('profile edit lives inside the profile sheet', async ({ page }, testInfo) => {
    skipUnlessPhone(testInfo);
    await page.goto('/app');

    await page.getByRole('button', { name: 'Choose kundli profile' }).click();
    await page.getByRole('button', { name: /Anika Rao/ }).click();
    await expect(page.getByRole('button', { name: 'Edit active kundli' })).toBeHidden();
    await page.getByRole('button', { name: 'Change active kundli profile' }).click();
    await expect(page.getByRole('button', { name: 'Edit profile' })).toBeVisible();
  });
});

test.describe('tablet and desktop shell', () => {
  test('keeps sidebar navigation and hides the mobile bottom nav', async ({ page }, testInfo) => {
    skipOnPhone(testInfo);
    await page.goto('/app');

    await expect(page.locator('app-sidebar')).toBeVisible();
    await expect(page.getByRole('navigation', { name: 'Primary navigation' })).toBeHidden();
    await expect(page.getByRole('navigation', { name: 'App navigation' })).toBeVisible();
    await expect(page.getByRole('button', { name: /AstroSpace/ })).toBeVisible();

    await expectNoHorizontalOverflow(page);
  });
});
