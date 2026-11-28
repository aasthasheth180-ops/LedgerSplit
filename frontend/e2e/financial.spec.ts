import { test, expect, type Page } from '@playwright/test'

const password = 'SyntheticE2ETest123!'
const baseURL = 'http://localhost:8081'

async function register(page: Page, name: string, email: string) {
  await page.goto('/register')
  await page.getByPlaceholder('Enter your full name').fill(name)
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.getByPlaceholder('At least 8 characters').fill(password)
  await page.getByPlaceholder('Re-enter your password').fill(password)
  await page.getByRole('checkbox').check()

  const responsePromise = page.waitForResponse(
    response => response.url().endsWith('/api/auth/register') &&
      response.request().method() === 'POST',
    { timeout: 30_000 }
  )
  await page.locator('button[type="submit"]').click()
  const response = await responsePromise
  expect(response.status()).toBe(201)
  await expect(page).toHaveURL(/\/login$/)
}

async function login(page: Page, email: string) {
  await page.goto('/login')
  await page.getByPlaceholder('you@example.com').fill(email)
  await page.getByPlaceholder('Enter your password', { exact: true }).fill(password)

  const responsePromise = page.waitForResponse(
    response => response.url().endsWith('/api/auth/login') &&
      response.request().method() === 'POST',
    { timeout: 30_000 }
  )
  await page.locator('button[type="submit"]').click()
  const response = await responsePromise
  expect(response.status()).toBe(200)
  await expect(page).toHaveURL(/\/expenses$/)
}

test('two users complete a shared financial journey', async ({ browser }) => {
  test.setTimeout(300_000)
  const suffix = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  const aliceEmail = `e2e_alice_${suffix}@example.com`
  const bobEmail = `e2e_bob_${suffix}@example.com`
  const groupName = `E2E Household ${suffix}`
  const expenseName = `E2E Groceries ${suffix}`
  const requestName = `E2E Repayment ${suffix}`

  const aliceContext = await browser.newContext({ baseURL })
  const bobContext = await browser.newContext({ baseURL })
  const alice = await aliceContext.newPage()
  const bob = await bobContext.newPage()

  try {
    await test.step('Register and authenticate two users', async () => {
      await register(alice, 'Alice E2E', aliceEmail)
      await register(bob, 'Bob E2E', bobEmail)
      await login(alice, aliceEmail)
      await login(bob, bobEmail)
    })

    await test.step('Create a shared group', async () => {
      await alice.goto('/groups/new')
      await alice.getByLabel('Group Name').fill(groupName)
      const member = alice.getByLabel('Member email')
      if (await member.count() === 0) {
        await alice.getByRole('button', { name: /Add Another Member/ }).click()
      }
      await member.first().fill(bobEmail)
      await alice.getByLabel('Default Group Currency').selectOption('USD')
      await alice.locator('button[type="submit"]').click()
      await expect(alice).toHaveURL(/\/groups$/)
      await expect(alice.getByRole('heading', { name: groupName, exact: true })).toBeVisible()
      await bob.goto('/groups')
      await expect(bob.getByRole('heading', { name: groupName, exact: true })).toBeVisible()
    })

    await test.step('Record a $100 equal-split expense', async () => {
      await alice.goto('/expenses/add')
      await alice.getByLabel('Target group', { exact: true }).selectOption({ label: `${groupName} · USD` })
      await alice.getByLabel('Description', { exact: true }).fill(expenseName)
      await alice.getByLabel(/Total Amount/).fill('100.00')
      await alice.getByRole('button', { name: /Groceries/ }).click()
      await alice.getByRole('button', { name: 'Split Equally' }).click()
      await expect(alice.getByRole('checkbox')).toHaveCount(2)
      for (const checkbox of await alice.getByRole('checkbox').all()) {
        await checkbox.check()
      }
      await alice.getByRole('button', { name: /Save & Record Expense/ }).click()
      await expect(alice).toHaveURL(/\/expenses$/)
      await expect(alice.getByText(expenseName, { exact: true })).toBeVisible()
      await bob.goto('/expenses')
      await expect(bob.getByText(expenseName, { exact: true })).toBeVisible()
    })

    await test.step('Create a $50 repayment request', async () => {
      await alice.goto('/payment-requests/new')
      await alice.getByLabel('Target Group').selectOption({ label: `${groupName} · USD` })
      await alice.getByLabel('Recipient Member').selectOption({ label: 'Bob E2E' })
      await alice.getByRole('button', { name: 'Use maximum' }).click()
      await expect(alice.getByLabel(/Requested Amount/)).toHaveValue('50.00')
      await alice.getByLabel('Optional description / reference').fill(requestName)
      await alice.getByRole('button', { name: 'Create Payment Request', exact: true }).click()
      await expect(alice).toHaveURL(/\/payment-requests$/)
      await bob.goto('/payment-requests')

      const requestRow = bob.getByRole('row').filter({ hasText: requestName })
      await expect(requestRow).toBeVisible()
      await expect(requestRow.getByText('Incoming', { exact: true })).toBeVisible()
      await expect(requestRow.getByText(/^pending$/i)).toBeVisible()
    })

    await test.step('Debtor reports external settlement', async () => {
      await bob.goto('/balances')
      bob.once('dialog', dialog => dialog.accept())
      await bob.getByRole('button', { name: 'Record Settlement', exact: true }).click()
      await expect(bob.getByText(/^pending$/i)).toBeVisible()
    })

    await test.step('Creditor confirms settlement', async () => {
      await alice.goto('/balances')
      alice.once('dialog', dialog => dialog.accept())
      await alice.getByRole('button', { name: 'Confirm', exact: true }).click()
      await expect(alice.getByText(/^confirmed$/i)).toBeVisible()
    })

    await test.step('Verify payment request fulfillment', async () => {
      await alice.goto('/payment-requests')
      await expect(alice.getByRole('row').filter({ hasText: requestName }).getByText(/^fulfilled$/i)).toBeVisible()
      await bob.goto('/payment-requests')
      await expect(bob.getByRole('row').filter({ hasText: requestName }).getByText(/^fulfilled$/i)).toBeVisible()
    })

    await test.step('Verify persistence in a fresh browser session', async () => {
      const freshContext = await browser.newContext({ baseURL })
      try {
        const freshPage = await freshContext.newPage()
        await login(freshPage, aliceEmail)
        await expect(freshPage.getByText(expenseName, { exact: true })).toBeVisible()
        await freshPage.goto('/payment-requests')
        await expect(freshPage.getByRole('row').filter({ hasText: requestName }).getByText(/^fulfilled$/i)).toBeVisible()
      } finally {
        await freshContext.close()
      }
    })
  } finally {
    await aliceContext.close()
    await bobContext.close()
  }
})
