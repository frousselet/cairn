"""Registry mapping an entity key to its :class:`EntityImporter` subclass."""

_REGISTRY = {}


def register(importer_cls):
    """Register an importer class. Usable as a decorator.

    >>> @register
    ... class SupplierImporter(EntityImporter):
    ...     entity_key = "supplier"
    """
    if not importer_cls.entity_key:
        raise ValueError("EntityImporter subclasses must define an entity_key.")
    _REGISTRY[importer_cls.entity_key] = importer_cls
    return importer_cls


def get(entity_key):
    """Return the importer class for ``entity_key`` or ``None``."""
    return _REGISTRY.get(entity_key)


def all_importers():
    """Return a copy of the registry (entity_key -> importer class)."""
    return dict(_REGISTRY)
