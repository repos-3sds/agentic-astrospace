import { expect, test, type Page, type Route } from '@playwright/test';

function phoneOnly(projectName: string): void {
  test.skip(projectName !== 'mobile-chrome-360', 'One phone exercises the stateful account journey');
}

test('registers, creates the first chart, logs out, and restores it on return', async ({
  page,
}, testInfo) => {
  phoneOnly(testInfo.project.name);
  await page.setViewportSize({ width: 375, height: 812 });
  const profiles: Record<string, unknown>[] = [];
  let profileLoads = 0;

  await page.route('**/api/v1/**', async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (url.pathname === '/api/v1/auth/config') {
      await route.fulfill({ json: { enabled: false } });
      return;
    }
    if (url.pathname === '/api/v1/kundlis' && request.method() === 'GET') {
      profileLoads += 1;
      await route.fulfill({ json: profiles });
      return;
    }
    if (url.pathname === '/api/v1/kundlis' && request.method() === 'POST') {
      const created = {
        id: 'journey-profile',
        ...request.postDataJSON(),
        sun_sign: 'Leo',
        moon_sign: 'Cancer',
        ascendant: 'Libra',
      };
      profiles.push(created);
      await route.fulfill({ status: 201, json: created });
      return;
    }
    await route.fulfill({ status: 503, json: { detail: 'Unavailable in lifecycle fixture' } });
  });

  await page.goto('/m/start');
  await page.getByRole('link', { name: 'Get started' }).click();
  await page.getByRole('textbox', { name: 'YOUR NAME' }).fill('Journey Test');
  await page.getByRole('textbox', { name: 'EMAIL' }).fill('journey@example.com');
  await page.getByRole('textbox', { name: /PASSWORD/ }).fill('Journey123!');
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page).toHaveURL(/\/m\/language$/);
  await page.getByRole('link', { name: 'Continue' }).click();
  await page.getByRole('link', { name: 'Continue' }).click();
  await page.getByRole('link', { name: 'I understand — continue' }).click();
  await page.getByRole('link', { name: 'Continue' }).click();

  await expect(page).toHaveURL(/\/m\/birth-details$/);
  await expect(page.getByRole('textbox', { name: 'WHO IS THIS FOR?' })).toHaveValue(
    /Journey Test/,
  );
  await page.getByRole('textbox', { name: 'PLACE OF BIRTH' }).fill('Vijayawada');
  await page.getByRole('button', { name: 'Cast my chart' }).click();
  await expect(page).toHaveURL(/\/m\/today$/);

  await page.getByRole('link', { name: 'More' }).click();
  await page.getByRole('link', { name: /Account & privacy/ }).click();
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page).toHaveURL(/\/m\/start$/);

  await page.getByRole('link', { name: 'I already have a space' }).click();
  await page.getByRole('textbox', { name: 'EMAIL' }).fill('journey@example.com');
  await page.getByRole('textbox', { name: /PASSWORD/ }).fill('Journey123!');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();

  await expect(page).toHaveURL(/\/m\/today$/);
  await expect.poll(() => profileLoads).toBeGreaterThanOrEqual(2);
  expect(profiles).toHaveLength(1);
});
