import { chromium } from 'playwright-core'

const url = process.argv[2] ?? 'http://localhost:3000'

async function main() {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  page.on('console', (msg) => {
    const args = msg.args()
    if (args.length) {
      Promise.all(args.map((arg) => arg.jsonValue().catch(() => arg.toString()))).then((values) => {
        console.log(`[browser ${msg.type()}]`, ...values)
      })
    } else {
      console.log(`[browser ${msg.type()}]`, msg.text())
    }
  })
  page.on('pageerror', (error) => {
    console.error('[browser error]', error)
  })
  await page.goto(url, { waitUntil: 'networkidle' })
  await page.waitForTimeout(5000)
  await browser.close()
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
