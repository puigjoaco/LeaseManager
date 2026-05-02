import { Badge } from './shared'
import { stamp } from './shared-utils'

type AssignmentItem = {
  role: string
  scope: string | null
  is_primary: boolean
}

type TabItem = {
  key: string
  label: string
}

export function WorkspaceHeader({
  userLabel,
  effectiveRole,
  assignments,
  lastLoadedAt,
  isRefreshing,
  onRefresh,
  onLogout,
}: {
  userLabel: string
  effectiveRole: string
  assignments: AssignmentItem[]
  lastLoadedAt: string | null
  isRefreshing: boolean
  onRefresh: () => void
  onLogout: () => void
}) {
  return (
    <header className="workspace-header">
      <div>
        <p className="section-tag">Backoffice</p>
        <h1>LeaseManager</h1>
        <p className="header-copy">{userLabel}</p>
        <div className="scope-strip">
          <Badge label={effectiveRole} tone="neutral" />
          {assignments.map((assignment, index) => (
            <Badge
              key={`${assignment.role}-${assignment.scope || 'global'}-${index}`}
              label={assignment.scope ? `${assignment.role} · ${assignment.scope}` : assignment.role}
              tone={assignment.is_primary ? 'positive' : 'neutral'}
            />
          ))}
        </div>
      </div>
      <div className="header-actions">
        <span className="refresh-label">{stamp(lastLoadedAt)}</span>
        <button type="button" className="button-secondary" onClick={onRefresh} disabled={isRefreshing}>
          {isRefreshing ? 'Actualizando...' : 'Actualizar'}
        </button>
        <button type="button" className="button-ghost" onClick={onLogout}>
          Salir
        </button>
      </div>
    </header>
  )
}

export function WorkspaceTabs({
  tabs,
  activeView,
  onSelect,
}: {
  tabs: TabItem[]
  activeView: string
  onSelect: (view: string) => void
}) {
  return (
    <section className="tab-strip">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          type="button"
          className={activeView === tab.key ? 'tab-button is-active' : 'tab-button'}
          onClick={() => onSelect(tab.key)}
        >
          {tab.label}
        </button>
      ))}
    </section>
  )
}

export function ContextBanner({
  label,
  onClear,
}: {
  label: string
  onClear: () => void
}) {
  return (
    <div className="context-banner">
      <span>{label}</span>
      <button type="button" className="button-ghost inline-action" onClick={onClear}>
        Limpiar contexto
      </button>
    </div>
  )
}

export function SectionToolbar({
  tag,
  title,
  placeholder,
  searchText,
  onSearchChange,
}: {
  tag: string
  title: string
  placeholder: string
  searchText: string
  onSearchChange: (value: string) => void
}) {
  return (
    <section className="section-toolbar">
      <div>
        <p className="section-tag">{tag}</p>
        <h2>{title}</h2>
      </div>
      <label className="search-field">
        <span>Buscar</span>
        <input value={searchText} onChange={(event) => onSearchChange(event.target.value)} placeholder={placeholder} />
      </label>
    </section>
  )
}
