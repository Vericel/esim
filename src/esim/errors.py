class InputError(Exception):
    """A user-correctable error detected before simulation execution."""


class SelectorError(InputError):
    """A TC or Rules selector cannot be located or is structurally invalid."""


class ConfigurationError(InputError):
    """A configuration value cannot produce a valid simulation invocation."""


class WaiverError(InputError):
    """A waiver source or pattern is invalid."""


class WorkspaceBusyError(InputError):
    """The simulation directory is already owned by another invocation."""


class CacheCompatibilityError(InputError):
    """A stage action cannot safely reuse the existing upstream cache."""
