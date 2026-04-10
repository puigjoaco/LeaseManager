from dataclasses import dataclass, field


@dataclass
class LegacySecretAsset:
    name: str
    category: str
    source_files: list[str] = field(default_factory=list)
    owner_system: str = 'LeaseManager'
    environments: list[str] = field(default_factory=list)
    status: str = 'discovered'


@dataclass
class LegacyIntegrationAsset:
    provider: str
    capability: str
    source_paths: list[str] = field(default_factory=list)
    status: str = 'discovered'


@dataclass
class LegacyTableInventory:
    table_name: str
    source: str
    migration_files: list[str] = field(default_factory=list)
    status: str = 'discovered'


@dataclass
class LegacyToCanonicalMapping:
    legacy_entity: str
    canonical_entity: str
    migration_state: str
    notes: str


@dataclass
class MigrationDecision:
    aggregate: str
    decision: str
    reason: str


@dataclass
class ManualResolutionQueue:
    aggregate: str
    reason: str
    resolution_owner: str
