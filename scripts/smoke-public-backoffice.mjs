import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { chromium } from 'playwright';

const DEFAULT_FRONTEND_URL = 'https://leasemanager-backoffice.vercel.app/';
const DEFAULT_API_BASE_URL = 'https://surprising-balance-production.up.railway.app';
const DEFAULT_ACCOUNTS = [
  { label: 'admin', username: 'demo-admin', password: 'demo12345', displayName: 'Demo Administrador Global', waitFor: 'overview' },
  { label: 'operator', username: 'demo-operador', password: 'demo12345', displayName: 'Demo Operador de Cartera', waitFor: 'overview' },
  { label: 'reviewer', username: 'demo-revisor', password: 'demo12345', displayName: 'Demo Revisor Fiscal Externo', waitFor: 'contabilidad' },
  { label: 'partner', username: 'demo-socio', password: 'demo12345', displayName: 'Demo Socio', waitFor: 'reporting' },
];

function parseArgs(argv) {
  const options = {
    frontendUrl: DEFAULT_FRONTEND_URL,
    apiBaseUrl: DEFAULT_API_BASE_URL,
    accounts: [],
    screenshotDir: path.resolve(process.cwd(), 'screenshots'),
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === '--frontend-url' && next) {
      options.frontendUrl = next;
      index += 1;
      continue;
    }
    if (arg === '--api-base-url' && next) {
      options.apiBaseUrl = next;
      index += 1;
      continue;
    }
    if (arg === '--username' && next) {
      const username = next;
      const password = argv[index + 2];
      if (!password) {
        throw new Error('--username requires a following password argument.');
      }
      options.accounts.push({ label: username, username, password });
      index += 2;
      continue;
    }
    if (arg === '--screenshot-dir' && next) {
      options.screenshotDir = path.resolve(next);
      index += 1;
      continue;
    }
  }

  if (!options.accounts.length) {
    options.accounts = [...DEFAULT_ACCOUNTS];
  }
  return options;
}

async function runSmoke({ frontendUrl, apiBaseUrl, account, screenshotDir }) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1200 } });
  const page = await context.newPage();
  page.setDefaultTimeout(180_000);
  const normalizedApiBaseUrl = apiBaseUrl.replace(/\/+$/, '');

  try {
    const start = Date.now();
    await page.goto(frontendUrl, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.body.innerText.includes('Continuar sesión'));
    await page.getByLabel('Usuario').fill(account.username);
    await page.getByLabel('Contraseña').fill(account.password);
    const loginRequest = page.waitForRequest((request) =>
      request.method() === 'POST'
      && request.url() === `${normalizedApiBaseUrl}/api/v1/auth/login/`
    );
    await page.getByRole('button', { name: 'Ingresar' }).click();
    await loginRequest;
    await page.waitForFunction((displayName) => document.body.innerText.includes(displayName), account.displayName);

    if (account.waitFor === 'contabilidad') {
      await page.waitForFunction(() => document.body.innerText.includes('Regímenes tributarios'));
      await page.waitForFunction(
        () =>
          !document.body.innerText.includes('Cargando catálogo contable...')
          && !document.body.innerText.includes('Cargando actividad contable...')
          && document.body.innerText.includes('Cierres mensuales'),
      );
    } else if (account.waitFor === 'reporting') {
      await page.waitForFunction(
        () =>
          document.body.innerText.includes('Resumen propio')
          && document.body.innerText.includes('Socio vinculado')
          && !document.body.innerText.includes('Sin resumen cargado')
          && !document.body.innerText.includes('RUT\nSin dato'),
      );
      await page.waitForTimeout(1_000);
    } else {
      await page.waitForFunction(
        () => !document.body.innerText.includes('Actualizando...') && document.body.innerText.includes('Actualizar'),
      );
      await page.waitForTimeout(2_000);
    }

    const body = await page.locator('body').innerText();
    const tabs = await page
      .locator('button')
      .evaluateAll((elements) => elements.map((element) => (element.textContent || '').trim()).filter(Boolean));

    await fs.mkdir(screenshotDir, { recursive: true });
    const screenshotPath = path.join(screenshotDir, `smoke-${account.label}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    return {
      ok: true,
      label: account.label,
      username: account.username,
      authFlow: 'ui-login',
      seconds: Number(((Date.now() - start) / 1000).toFixed(1)),
      tabs,
      dashboard: {
        propiedades: /Propiedades activas\s+(\d+)/.exec(body)?.[1] || null,
        contratos: /Contratos vigentes\s+(\d+)/.exec(body)?.[1] || null,
        pagos: /Pagos pendientes\s+(\d+)/.exec(body)?.[1] || null,
        dtes: /DTE borrador\s+(\d+)/.exec(body)?.[1] || null,
      },
      hasReadonlyBanner: body.toLowerCase().includes('solo lectura'),
      screenshotPath,
      excerpt: body.slice(0, 5000),
    };
  } catch (error) {
    return {
      ok: false,
      label: account.label,
      username: account.username,
      authFlow: 'ui-login',
      error: String(error),
    };
  } finally {
    await context.close();
    await browser.close();
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const results = [];
  for (const account of options.accounts) {
    // Keep the run sequential to reduce noise from concurrent public requests.
    results.push(await runSmoke({ ...options, account }));
  }
  console.log(JSON.stringify(results, null, 2));
  if (results.some((result) => !result.ok)) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
