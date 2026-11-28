import { test, expect } from '@playwright/test'

test('backend readiness is healthy', async ({ request }) => {
  const response = await request.get('/api/health/ready')

  expect(response.status()).toBe(200)
  expect(await response.json()).toEqual({
    status: 'ready',
  })
})

test('unauthenticated users cannot access protected pages', async ({ page }) => {
  const routes = [
    '/expenses',
    '/expenses/add',
    '/groups',
    '/groups/new',
    '/balances',
    '/payment-requests',
    '/payment-requests/new',
    '/settings',
  ]

  for (const route of routes) {
    await page.goto(route)
    await expect(page).toHaveURL(/\/login(?:[?#].*)?$/)
  }
})

test('landing page loads successfully', async ({ page }) => {
  const response = await page.goto('/')

  expect(response?.status()).toBe(200)
  await expect(page.locator('body')).toBeVisible()
})