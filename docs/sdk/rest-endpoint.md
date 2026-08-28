# Adding a REST endpoint

Every feature is expected to be reachable on `/api/v1/`. This is not a
nice-to-have : a capability that exists only in the interface makes the API a
partial view of the platform, and the partiality is discovered by whoever
depends on it, at the worst moment.

The complete published route table is
[reference/generated/rest-endpoints.md](../reference/generated/rest-endpoints.md),
generated from the URL resolver.

## Where the files go

```
<app>/api/
├── serializers.py    one serializer per resource
├── views.py          the viewsets
└── urls.py           a DRF router, mounted at /api/v1/<app>/ from core/urls.py
```

## 1. The serializer

```python
class SupplierAttestationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierAttestation
        fields = [
            "id", "reference", "supplier", "framework", "valid_until",
            "workflow_state", "scopes", "created_at", "updated_at", "version",
        ]
        read_only_fields = ["id", "reference", "workflow_state", "created_at",
                            "updated_at", "version"]
```

`workflow_state` is **always** read-only. A state change goes through the
transition route, never through a `PATCH`, because the transition is where the
permission gate, the mandatory comment and the recorded lifecycle event live.
Making it writable does not add a convenience, it removes a control.

Computed fields are read-only for the same reason : a derived due date that a
client can set is a due date nobody can trust.

## 2. The viewset

Give the app one base class that fixes the permission module and the shared
action map, and have every viewset extend it. That is what stops the thirteen
viewsets of a module from drifting apart one at a time.

```python
class _AssetsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "assets"
    custom_action_map = {
        "transition": "update",
        # BatchCreateMixin creates rows, so it consumes `create`. Without this
        # entry the action falls through to the HTTP method and a batch POST
        # would be gated on `update`.
        "batch_create": "create",
    }


class SupplierAttestationViewSet(
    ScopeFilterAPIMixin, LifecycleAPIMixin, HistoryAPIMixin, BatchCreateMixin,
    _AssetsViewSet,
):
    queryset = SupplierAttestation.objects.all()
    serializer_class = SupplierAttestationSerializer
    permission_feature = "supplier_attestation"
    filterset_fields = ["supplier", "framework", "workflow_state"]
    search_fields = ["reference", "supplier__name"]
    ordering_fields = ["valid_until", "created_at"]
```

What each mixin buys you:

| Mixin | Adds |
| --- | --- |
| `ScopeFilterAPIMixin` | Tenancy filtering. On a model that is not a `ScopedModel`, set `scope_parent_lookup` to the path to the scoped parent |
| `LifecycleAPIMixin` | `POST .../<uuid>/transition/`, routed through `transition_to(enforce_permission=True)` |
| `HistoryAPIMixin` | `GET .../<uuid>/history/` |
| `BatchCreateMixin` | Batch creation, up to 500 objects, non-atomic with partial success reporting |

An entity that runs no lifecycle simply does not mix in `LifecycleAPIMixin`, and
no `transition/` route is generated for it. Absence is the mechanism; there is
no flag to remember.

`ModulePermission` resolves `{module}.{feature}.{action}` from these attributes,
mapping DRF actions to permission actions (`list` and `retrieve` to `read`,
`create` to `create`, `update` and `partial_update` to `update`, `destroy` to
`delete`). A custom `@action` that is not in the map falls through to the HTTP
method, which is usually wrong : add it to `custom_action_map` explicitly.

## 3. Declare tenancy, do not assume it

The failure this guards against is **silent**. A child model with no
`scope_parent_lookup` makes `ScopeFilterAPIMixin` a no-op, and the register is
then readable from outside its perimeter with no error anywhere.

The incidents module handles this by refusing at import time, in
`__init_subclass__`, any viewset whose tenancy does not add up : scope-filtered
but resolving no path to `context.Scope`, or claiming exemption over a model
that does resolve one. Copy that pattern. It turns a security bug into a
start-up crash, and it makes the two legitimate exemptions (shared catalogues)
read as decisions rather than as the same oversight.

```python
scope_filtered = False   # a shared catalogue, deliberately not tenanted
```

## 4. Route it

```python
router = DefaultRouter()
router.register(r"supplier-attestations", SupplierAttestationViewSet,
                basename="supplier-attestation")
urlpatterns = [path("", include(router.urls))]
```

Register resources **flat**, not nested under a parent. A child is filtered by
its parent (`?supplier=<uuid>`) rather than addressed through it, so every row
keeps one stable URL and a client never has to know two ways to reach the same
record.

## 5. Append-only registers

When a resource is a ledger, restrict the verbs at the **routing** layer rather
than refusing them in a handler:

```python
http_method_names = ["get", "post", "head", "options"]
```

`PUT`, `PATCH` and `DELETE` then generate no route at all and answer `405`.
Refusing in a handler leaves a route that exists and could be re-enabled by a
later refactor; generating no route cannot be undone by accident.

## 6. Files

Never put a file in a payload, and never serve one from a guessable media URL.
Stream it from a dedicated action resolved through the scoped queryset and
permission-checked:

```python
@action(detail=True, methods=["get"])
def download(self, request, pk=None):
    obj = self.get_object()          # already scope-filtered and permission-checked
    ...
```

## 7. The error contract

| Situation | Status |
| --- | --- |
| Not permitted to perform the transition | `403` |
| A gate refused the move, or the payload is invalid | `400` |
| A write-once or append-only field was targeted | `409` |
| Out of scope, or the file is gone | `404` |
| A verb the resource does not publish | `405` |

A governance refusal is never a `500`. If it is, the check is in the wrong place.

## 8. Regenerate and test

```bash
python manage.py generate_docs
```

Tests belong in `<app>/tests/test_api.py` and must cover, at minimum : an
unauthorised caller is refused; a caller outside the scope sees nothing;
`workflow_state` cannot be patched; the transition route enforces its permission;
and, for a ledger, that `PUT`, `PATCH` and `DELETE` answer `405`.

## Checklist

- [ ] Serializer written, `workflow_state` and computed fields read-only
- [ ] Viewset extends the app's base, declares `permission_feature`
- [ ] Tenancy declared : scope-filtered, or exemption stated explicitly
- [ ] Custom actions added to `custom_action_map`
- [ ] Registered flat on the router
- [ ] Filters, search and ordering declared
- [ ] Files streamed from a permission-checked action, never in the payload
- [ ] Matching [MCP tool](mcp-tool.md) added
- [ ] `generate_docs` re-run and committed
- [ ] Tests cover permission, tenancy, read-only fields and transitions
