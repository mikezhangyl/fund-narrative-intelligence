class PipelineError(Exception):
    """Base exception for controlled pipeline failures."""


class FixtureNotFoundError(PipelineError):
    """Raised when a requested local fixture does not exist."""


class ProviderContractError(PipelineError):
    """Raised when provider data does not satisfy the V1 contract."""


class ProviderFetchError(PipelineError):
    """Raised when a real provider fetch fails."""
