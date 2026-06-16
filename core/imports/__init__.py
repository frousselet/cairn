"""Generic, declarative bulk-import framework (entity by entity).

Each importable entity declares a subclass of :class:`~core.imports.base.EntityImporter`
listing its CSV columns and how to resolve related objects, then registers it with
:func:`core.imports.registry.register`. The generic views, URLs and templates handle
the upload -> preview -> confirm wizard for every registered entity.
"""
