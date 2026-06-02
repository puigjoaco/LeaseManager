import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

import { chromium } from 'playwright';

const DEFAULT_ACCOUNTS = [
  { label: 'admin', username: 'demo-admin', password: 'demo12345', displayName: 'Demo Administrador Global', waitFor: 'overview' },
  { label: 'operator', username: 'demo-operador', password: 'demo12345', displayName: 'Demo Operador de Cartera', waitFor: 'overview' },
  { label: 'reviewer', username: 'demo-revisor', password: 'demo12345', displayName: 'Demo Revisor Fiscal Externo', waitFor: 'contabilidad' },
  { label: 'partner', username: 'demo-socio', password: 'demo12345', displayName: 'Demo Socio', waitFor: 'reporting' },
];

function parseArgs(argv) {
  const options = {
    frontendUrl: '',
    apiBaseUrl: '',
    accounts: [],
    allowExternal: false,
    screenshotDir: path.resolve(process.cwd(), 'screenshots'),
    evidenceSourceKind: '',
    authorizationRef: '',
    environmentRef: '',
    targetRef: '',
    responsibleRef: '',
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === '--allow-external') {
      options.allowExternal = true;
      continue;
    }
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
      options.accounts.push({ label: `custom-${options.accounts.length + 1}`, username, password });
      index += 2;
      continue;
    }
    if (arg === '--screenshot-dir' && next) {
      options.screenshotDir = path.resolve(next);
      index += 1;
      continue;
    }
    if (arg === '--evidence-source-kind' && next) {
      options.evidenceSourceKind = next;
      index += 1;
      continue;
    }
    if (arg === '--authorization-ref' && next) {
      options.authorizationRef = next;
      index += 1;
      continue;
    }
    if (arg === '--environment-ref' && next) {
      options.environmentRef = next;
      index += 1;
      continue;
    }
    if (arg === '--target-ref' && next) {
      options.targetRef = next;
      index += 1;
      continue;
    }
    if (arg === '--responsible-ref' && next) {
      options.responsibleRef = next;
      index += 1;
      continue;
    }
    throw new Error(`Unknown or incomplete argument: ${arg}`);
  }

  validateTargetUrls(options);
  validateEvidenceOptions(options);
  if (!options.accounts.length) {
    options.accounts = [...DEFAULT_ACCOUNTS];
  }
  return options;
}

function isLocalUrl(value) {
  try {
    const parsed = new URL(value);
    return ['localhost', '127.0.0.1', '::1'].includes(parsed.hostname);
  } catch {
    return false;
  }
}

function validateTargetUrls(options) {
  if (!options.frontendUrl || !options.apiBaseUrl) {
    throw new Error('Explicit --frontend-url and --api-base-url are required.');
  }
  const targetsAreLocal = isLocalUrl(options.frontendUrl) && isLocalUrl(options.apiBaseUrl);
  if (!targetsAreLocal && !options.allowExternal) {
    throw new Error('External smoke targets require explicit --allow-external.');
  }
}

function shouldEmitEvidenceEnvelope(options) {
  return Boolean(
    options.evidenceSourceKind
      || options.authorizationRef
      || options.environmentRef
      || options.targetRef
      || options.responsibleRef,
  );
}

function isNonSensitiveReference(value) {
  return Boolean(value && !/(?:\:\/\/|@|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial)/i.test(value));
}

function validateEvidenceOptions(options) {
  if (!shouldEmitEvidenceEnvelope(options)) {
    return;
  }
  const allowedSourceKinds = new Set([
    'public_smoke_autorizado',
    'ambiente_autorizado',
    'staging_autorizado',
    'real_autorizado',
  ]);
  if (!options.evidenceSourceKind) {
    options.evidenceSourceKind = 'public_smoke_autorizado';
  }
  if (!allowedSourceKinds.has(options.evidenceSourceKind)) {
    throw new Error('Evidence source kind is not accepted for public smoke closure.');
  }
  for (const [name, value] of [
    ['authorization-ref', options.authorizationRef],
    ['environment-ref', options.environmentRef],
    ['target-ref', options.targetRef],
  ]) {
    if (!isNonSensitiveReference(value)) {
      throw new Error(`--${name} must be a non-sensitive evidence reference, not a URL or secret.`);
    }
  }
  if (options.responsibleRef && !isNonSensitiveReference(options.responsibleRef)) {
    throw new Error('--responsible-ref must be non-sensitive when provided.');
  }
}

function assertTextIncludes(body, expected, message) {
  if (!body.includes(expected)) {
    throw new Error(message);
  }
}

function assertTextExcludes(body, unexpected, message) {
  if (body.includes(unexpected)) {
    throw new Error(message);
  }
}

function validateSmokeBody(account, body) {
  if (account.waitFor === 'contabilidad') {
    assertTextIncludes(
      body,
      'Configuración fiscal, eventos, asientos y cierres',
      'Reviewer accounting workspace was not ready.',
    );
    assertTextExcludes(body, 'Cargando catálogo contable', 'Reviewer accounting catalog was still loading.');
    assertTextExcludes(body, 'Cargando actividad contable', 'Reviewer accounting activity was still loading.');
    return;
  }

  if (account.waitFor === 'reporting') {
    assertTextIncludes(body, 'Resumen propio', 'Partner reporting summary was not ready.');
    assertTextIncludes(body, 'Socio vinculado', 'Partner linked owner block was not ready.');
    assertTextExcludes(body, 'Sin resumen cargado', 'Partner reporting summary did not load.');
    if (/RUT\r?\nSin dato/.test(body)) {
      throw new Error('Partner RUT block did not load.');
    }
    return;
  }

  if (account.label === 'operator') {
    assertTextIncludes(body, 'Resoluciones abiertas', 'Operator operational summary was not ready.');
    assertTextExcludes(body, 'Contabilidad', 'Operator saw restricted accounting navigation.');
    return;
  }

  if (account.label === 'admin') {
    assertTextIncludes(body, 'conciliacion.ingreso desconocido', 'Admin manual backlog category was not ready.');
    assertTextExcludes(body, 'Actualizando detalle de', 'Admin manual backlog kept a loading placeholder.');
  }
}

function toPublicSmokeResult(result) {
  const publicResult = {
    ok: Boolean(result.ok),
    label: result.label,
    authFlow: result.authFlow,
  };

  if (typeof result.seconds === 'number') {
    publicResult.seconds = result.seconds;
  }
  if (result.dashboard) {
    publicResult.dashboard = result.dashboard;
  }
  if (typeof result.hasReadonlyBanner === 'boolean') {
    publicResult.hasReadonlyBanner = result.hasReadonlyBanner;
  }
  if (result.screenshotCaptured) {
    publicResult.screenshotCaptured = true;
  }
  if (!result.ok) {
    publicResult.errorCode = result.errorCode || 'smoke_step_failed';
  }
  return publicResult;
}

function buildSmokeOutput(options, results) {
  const publicResults = results.map(toPublicSmokeResult);
  if (!shouldEmitEvidenceEnvelope(options)) {
    return publicResults;
  }
  return {
    source_kind: options.evidenceSourceKind,
    authorization_ref: options.authorizationRef,
    environment_ref: options.environmentRef,
    target_ref: options.targetRef,
    responsible_ref: options.responsibleRef || undefined,
    generated_at: new Date().toISOString(),
    results: publicResults,
  };
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
    validateSmokeBody(account, body);

    await fs.mkdir(screenshotDir, { recursive: true });
    const screenshotPath = path.join(screenshotDir, `smoke-${account.label}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    return {
      ok: true,
      label: account.label,
      authFlow: 'ui-login',
      seconds: Number(((Date.now() - start) / 1000).toFixed(1)),
      dashboard: {
        propiedades: /Propiedades activas\s+(\d+)/.exec(body)?.[1] || null,
        contratos: /Contratos vigentes\s+(\d+)/.exec(body)?.[1] || null,
        pagos: /Pagos pendientes\s+(\d+)/.exec(body)?.[1] || null,
        dtes: /DTE borrador\s+(\d+)/.exec(body)?.[1] || null,
      },
      hasReadonlyBanner: body.toLowerCase().includes('solo lectura'),
      screenshotCaptured: true,
    };
  } catch (error) {
    return {
      ok: false,
      label: account.label,
      authFlow: 'ui-login',
      errorCode: 'smoke_step_failed',
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
  const output = buildSmokeOutput(options, results);
  console.log(JSON.stringify(output, null, 2));
  if (results.some((result) => !result.ok)) {
    process.exitCode = 1;
  }
}

export {
  buildSmokeOutput,
  isNonSensitiveReference,
  parseArgs,
  toPublicSmokeResult,
  validateSmokeBody,
};

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (invokedPath && fileURLToPath(import.meta.url) === invokedPath) {
  main().catch((error) => {
    console.error(error.message || error);
    process.exit(1);
  });
}
