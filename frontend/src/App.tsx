import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type HealthPayload = {
  service: string
  status: string
  environment: string
  services: Record<string, { status: string; detail?: string }>
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function App() {
  const [health, setHealth] = useState<HealthPayload | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/health/`)
      .then((response) => response.json())
      .then((data: HealthPayload) => setHealth(data))
      .catch(() =>
        setHealth({
          service: 'leasemanager-api',
          status: 'unreachable',
          environment: 'unknown',
          services: {
            database: { status: 'down' },
            redis: { status: 'down' },
          },
        }),
      )
  }, [])

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoginError(null)

    const response = await fetch(`${API_BASE_URL}/api/v1/auth/login/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    })

    if (!response.ok) {
      setLoginError('No se pudo autenticar contra la API base.')
      return
    }

    const data = await response.json()
    setToken(data.token)
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <p className="eyebrow">LeaseManager v1</p>
        <h1>Greenfield del nuevo sistema dentro de Produccion 1.0</h1>
        <p className="lead">
          Shell inicial del backoffice para la nueva plataforma canónica. Este frontend se
          conecta a la PlataformaBase del backend Django/DRF y servirá como base del sistema
          operacional nuevo.
        </p>
      </section>

      <section className="grid">
        <article className="card">
          <h2>Estado base</h2>
          <p className="muted">
            Verificación rápida de API, base de datos y Redis del sistema nuevo.
          </p>
          <div className="status-list">
            <div className="status-row">
              <span>API</span>
              <strong>{health?.status || 'cargando'}</strong>
            </div>
            <div className="status-row">
              <span>DB</span>
              <strong>{health?.services.database.status || 'cargando'}</strong>
            </div>
            <div className="status-row">
              <span>Redis</span>
              <strong>{health?.services.redis.status || 'cargando'}</strong>
            </div>
          </div>
        </article>

        <article className="card">
          <h2>Login técnico</h2>
          <p className="muted">
            Punto mínimo para validar autenticación contra <code>/api/v1/auth/login/</code>.
          </p>
          <form className="login-form" onSubmit={handleLogin}>
            <label>
              <span>Usuario</span>
              <input value={username} onChange={(event) => setUsername(event.target.value)} />
            </label>
            <label>
              <span>Contraseña</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button type="submit">Autenticar</button>
          </form>
          {loginError && <p className="error">{loginError}</p>}
          {token && <p className="success">Token emitido correctamente para el shell inicial.</p>}
        </article>
      </section>

      <section className="card roadmap">
        <h2>Orden de construcción</h2>
        <ol>
          <li>PlataformaBase</li>
          <li>Patrimonio</li>
          <li>Operacion</li>
          <li>Contratos</li>
          <li>CobranzaActiva</li>
          <li>Conciliacion</li>
          <li>Contabilidad</li>
          <li>Documentos</li>
          <li>Canales</li>
          <li>SII</li>
          <li>Reporting</li>
        </ol>
      </section>
    </main>
  )
}

export default App

