import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import { chromium } from 'playwright';

const DEFAULT_FRONTEND_URL = 'https://leasemanager-backoffice.vercel.app/';
const DEFAULT_API_BASE_URL = 'https://surprising-balance-production.up.railway.app';
const DEFAULT_ACCOUNTS = [
  { label: 'admin', username: 'demo-admin', password: 'demo12345', displayName: 'Demo Administrador Global', waitFor: 'overview' },
  { label: 'reviewer', username: 'demo-revisor', password: 'demo12345', displayName: 'Demo Revisor Fiscal Externo', waitFor: 'contabilidad' },
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

async function fetchToken(apiBaseUrl, username, password) {
  const response = await fetch(`${apiBaseUrl}/api/v1/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error(`Login failed for ${username}: HTTP ${response.status}`);
  }
  const payload = await response.json();
  return payload;
}

async function runSmoke({ frontendUrl, apiBaseUrl, account, screenshotDir }) {
  const session = await fetchToken(apiBaseUrl, account.username, account.password);
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  page.setDefaultTimeout(180_000);

  try {
    const start = Date.now();
    await page.goto(frontendUrl, { waitUntil: 'domcontentloaded' });
    await page.evaluate(({ storedToken, storedUser, bootstrap }) => {
      localStorage.setItem('leasemanager.auth.token', storedToken);
      localStorage.setItem('leasemanager.auth.user', JSON.stringify(storedUser));
      const loadedAt = new Date().toISOString();
      if (bootstrap?.overview) {
        localStorage.setItem(
          `leasemanager.overview:${storedUser.id}:${storedUser.username}:${storedUser.default_role_code}`,
          JSON.stringify({
            dashboard: bootstrap.overview.dashboard ?? null,
            manualSummary: bootstrap.overview.manual_summary ?? null,
            lastLoadedAt: loadedAt,
          }),
        );
      }
      if (bootstrap?.control) {
        localStorage.setItem(
          `leasemanager.control:${storedUser.id}:${storedUser.username}:${storedUser.default_role_code}`,
          JSON.stringify({
            empresas: bootstrap.control.empresas,
            regimenesTributarios: bootstrap.control.regimenes_tributarios,
            configuracionesFiscales: bootstrap.control.configuraciones_fiscales,
            cuentasContables: bootstrap.control.cuentas_contables,
            reglasContables: bootstrap.control.reglas_contables,
            matricesReglas: bootstrap.control.matrices_reglas,
            eventosContables: bootstrap.control.eventos_contables,
            asientosContables: bootstrap.control.asientos_contables,
            obligacionesMensuales: bootstrap.control.obligaciones_mensuales,
            cierresMensuales: bootstrap.control.cierres_mensuales,
            lastLoadedAt: loadedAt,
          }),
        );
      }
    }, { storedToken: session.token, storedUser: session.user, bootstrap: session.bootstrap || null });
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction((displayName) => document.body.innerText.includes(displayName), account.displayName);

    if (account.waitFor === 'contabilidad') {
      await page.waitForFunction(() => document.body.innerText.includes('Regímenes tributarios'));
      await page.waitForFunction(
        () =>
          !document.body.innerText.includes('Cargando catálogo contable...')
          && !document.body.innerText.includes('Cargando actividad contable...')
          && document.body.innerText.includes('Cierres mensuales'),
      );
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
      error: String(error),
    };
  } finally {
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
