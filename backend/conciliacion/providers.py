from typing import Protocol


class ProviderBancario(Protocol):
    provider_key: str

    def sync_movimientos(self, cuenta_recaudadora, rango):
        ...

    def sync_saldos(self, cuenta_recaudadora):
        ...

    def validate_connectivity(self, cuenta_recaudadora):
        ...

    def describe_capabilities(self):
        ...

