import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  buildSmokeOutput,
  parseArgs,
  toPublicSmokeResult,
  validateSmokeBody,
} from '../smoke-public-backoffice.mjs';

test('public smoke result strips operational diagnostics from evidence output', () => {
  const publicResult = toPublicSmokeResult({
    ok: true,
    label: 'admin',
    username: 'demo-admin',
    authFlow: 'ui-login',
    seconds: 4.2,
    tabs: ['Contabilidad', 'Reporting'],
    dashboard: { propiedades: '2', contratos: '3', pagos: '5', dtes: null },
    hasReadonlyBanner: false,
    screenshotPath: 'D:/private/screenshots/smoke-admin.png',
    screenshotCaptured: true,
    excerpt: 'body text with operational details',
    error: 'raw browser failure with URL https://example.test/?token=dummy',
  });

  assert.deepEqual(publicResult, {
    ok: true,
    label: 'admin',
    authFlow: 'ui-login',
    seconds: 4.2,
    dashboard: { propiedades: '2', contratos: '3', pagos: '5', dtes: null },
    hasReadonlyBanner: false,
    screenshotCaptured: true,
  });
});

test('public smoke failure output keeps only a stable error code', () => {
  const publicResult = toPublicSmokeResult({
    ok: false,
    label: 'operator',
    username: 'demo-operador',
    authFlow: 'ui-login',
    error: 'Timeout at https://public.example.test/dashboard?token=dummy',
    screenshotPath: 'D:/private/screenshots/smoke-operator.png',
    excerpt: 'restricted body text',
  });

  assert.deepEqual(publicResult, {
    ok: false,
    label: 'operator',
    authFlow: 'ui-login',
    errorCode: 'smoke_step_failed',
  });
});

test('evidence envelope contains only safe smoke result fields', () => {
  const output = buildSmokeOutput(
    {
      evidenceSourceKind: 'public_smoke_autorizado',
      authorizationRef: 'smoke-authz-v1',
      environmentRef: 'staging-env-v1',
      targetRef: 'deploy-target-v1',
      responsibleRef: 'ops-owner-v1',
    },
    [
      {
        ok: true,
        label: 'admin',
        username: 'demo-admin',
        authFlow: 'ui-login',
        screenshotPath: 'D:/private/screenshots/smoke-admin.png',
        screenshotCaptured: true,
        excerpt: 'dashboard body',
      },
    ],
  );
  const serialized = JSON.stringify(output);

  assert.equal(output.source_kind, 'public_smoke_autorizado');
  assert.equal(output.authorization_ref, 'smoke-authz-v1');
  assert.equal(output.results[0].screenshotCaptured, true);
  assert.equal(serialized.includes('username'), false);
  assert.equal(serialized.includes('demo-admin'), false);
  assert.equal(serialized.includes('excerpt'), false);
  assert.equal(serialized.includes('dashboard body'), false);
  assert.equal(serialized.includes('screenshotPath'), false);
  assert.equal(serialized.includes('D:/private'), false);
});

test('screen assertions stay inside the smoke script instead of evidence output', () => {
  assert.doesNotThrow(() =>
    validateSmokeBody(
      { label: 'admin', waitFor: 'overview' },
      'Actualizar\nconciliacion.ingreso desconocido\nResoluciones abiertas',
    ),
  );
  assert.throws(
    () => validateSmokeBody({ label: 'operator', waitFor: 'overview' }, 'Resoluciones abiertas\nContabilidad'),
    /restricted accounting navigation/,
  );
});

test('custom account labels do not reuse the provided username', () => {
  const options = parseArgs([
    '--frontend-url',
    'http://localhost:5173',
    '--api-base-url',
    'http://127.0.0.1:8000',
    '--username',
    'persona@example.test',
    'dummy-password',
  ]);

  assert.equal(options.accounts[0].label, 'custom-1');
  assert.equal(options.accounts[0].username, 'persona@example.test');
});
