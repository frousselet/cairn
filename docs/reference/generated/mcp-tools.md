<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tools

Cairn's MCP server exposes the whole platform to AI assistants and scripts over JSON-RPC 2.0. Every tool runs as the calling user : the permission column below is enforced by the `@require_perm` decorator, and scope-based tenancy filters the rows on top of it.

Transport, authentication and client setup are in [../mcp-server.md](../mcp-server.md).

**735 tools** are registered, across **9 modules**. Most entities carry the same surface : `list_*`, `get_*`, `create_*`, `batch_create_*`, `update_*`, `delete_*`, plus `*_transition`, `*_allowed_transitions` and `*_history` when the entity runs a lifecycle.

## Modules

| Module | Tools | Parameter reference |
| --- | --- | --- |
| Assets | 136 | [mcp-tools-assets.md](mcp-tools-assets.md) |
| Compliance | 64 | [mcp-tools-compliance.md](mcp-tools-compliance.md) |
| Governance and context | 126 | [mcp-tools-context.md](mcp-tools-context.md) |
| General | 14 | [mcp-tools-general.md](mcp-tools-general.md) |
| Incidents | 103 | [mcp-tools-incidents.md](mcp-tools-incidents.md) |
| Reports and management review | 18 | [mcp-tools-reports.md](mcp-tools-reports.md) |
| Risks | 222 | [mcp-tools-risks.md](mcp-tools-risks.md) |
| System and administration | 10 | [mcp-tools-system.md](mcp-tools-system.md) |
| Trust Center | 42 | [mcp-tools-trust-center.md](mcp-tools-trust-center.md) |

## Assets

| Tool | Permission | Description |
| --- | --- | --- |
| `asset_dependency_allowed_transitions` | `assets.dependency.read` | List the lifecycle transitions the caller may perform on a asset dependency from its current state. |
| `asset_group_allowed_transitions` | `assets.group.read` | List the lifecycle transitions the caller may perform on a asset group from its current state. |
| `batch_create_asset_dependencys` | `assets.dependency.create` | Create or upsert multiple asset dependencys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_asset_groups` | `assets.group.create` | Create or upsert multiple asset groups in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_asset_valuations` | `assets.essential_asset.create` | Create or upsert multiple asset valuations in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_certificates` | `assets.certificate.create` | Create or upsert multiple certificates in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_contracts` | `assets.contract.create` | Create or upsert multiple contracts in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_essential_assets` | `assets.essential_asset.create` | Create or upsert multiple essential assets in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_site_asset_dependencys` | `assets.dependency.create` | Create or upsert multiple site asset dependencys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_site_supplier_dependencys` | `assets.supplier_dependency.create` | Create or upsert multiple site supplier dependencys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_supplier_contacts` | `assets.supplier.create` | Create or upsert multiple supplier contacts in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_supplier_dependencys` | `assets.supplier_dependency.create` | Create or upsert multiple supplier dependencys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_supplier_requirement_reviews` | `assets.supplier.create` | Create or upsert multiple supplier requirement reviews in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_supplier_requirements` | `assets.supplier.create` | Create or upsert multiple supplier requirements in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_supplier_subprocessors` | `assets.supplier.create` | Create or upsert multiple supplier subprocessors in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_supplier_type_requirements` | `assets.config.create` | Create or upsert multiple supplier type requirements in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_supplier_types` | `assets.config.create` | Create or upsert multiple supplier types in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_suppliers` | `assets.supplier.create` | Create or upsert multiple suppliers in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_support_assets` | `assets.support_asset.create` | Create or upsert multiple support assets in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `certificate_allowed_transitions` | `assets.certificate.read` | List the lifecycle transitions the caller may perform on a certificate from its current state. |
| `contract_allowed_transitions` | `assets.contract.read` | List the lifecycle transitions the caller may perform on a contract from its current state. |
| `create_asset_dependency` | `assets.dependency.create` | Create a new asset dependency |
| `create_asset_group` | `assets.group.create` | Create a new asset group |
| `create_asset_valuation` | `assets.essential_asset.create` | Create a new asset valuation |
| `create_certificate` | `assets.certificate.create` | Create a new certificate |
| `create_contract` | `assets.contract.create` | Create a new contract |
| `create_essential_asset` | `assets.essential_asset.create` | Create a new essential asset |
| `create_site_asset_dependency` | `assets.dependency.create` | Create a new site asset dependency |
| `create_site_supplier_dependency` | `assets.supplier_dependency.create` | Create a new site supplier dependency |
| `create_supplier` | `assets.supplier.create` | Create a new supplier. Optionally provide 'image_url' (a public URL pointing to an image file) to set the supplier logo. The image will be downloaded, resized to 128x128, and 64x64, 32x32, 16x16 variants will be generated automatically. Prefer 'image_url' over 'update_supplier_logo' when the logo is available as a URL. |
| `create_supplier_contact` | `assets.supplier.create` | Create a new supplier contact |
| `create_supplier_dependency` | `assets.supplier_dependency.create` | Create a new supplier dependency |
| `create_supplier_requirement` | `assets.supplier.create` | Create a new supplier requirement |
| `create_supplier_requirement_review` | `assets.supplier.create` | Create a new supplier requirement review |
| `create_supplier_subprocessor` | `assets.supplier.create` | Create a new supplier subprocessor |
| `create_supplier_type` | `assets.config.create` | Create a new supplier type |
| `create_supplier_type_requirement` | `assets.config.create` | Create a new supplier type requirement |
| `create_support_asset` | `assets.support_asset.create` | Create a new support asset |
| `delete_asset_dependency` | `assets.dependency.delete` | Delete a asset dependency |
| `delete_asset_group` | `assets.group.delete` | Delete a asset group |
| `delete_asset_valuation` | `assets.essential_asset.delete` | Delete a asset valuation |
| `delete_certificate` | `assets.certificate.delete` | Delete a certificate |
| `delete_contract` | `assets.contract.delete` | Delete a contract |
| `delete_essential_asset` | `assets.essential_asset.delete` | Delete a essential asset |
| `delete_site_asset_dependency` | `assets.dependency.delete` | Delete a site asset dependency |
| `delete_site_supplier_dependency` | `assets.supplier_dependency.delete` | Delete a site supplier dependency |
| `delete_supplier` | `assets.supplier.delete` | Delete a supplier |
| `delete_supplier_contact` | `assets.supplier.delete` | Delete a supplier contact |
| `delete_supplier_dependency` | `assets.supplier_dependency.delete` | Delete a supplier dependency |
| `delete_supplier_requirement` | `assets.supplier.delete` | Delete a supplier requirement |
| `delete_supplier_requirement_review` | `assets.supplier.delete` | Delete a supplier requirement review |
| `delete_supplier_subprocessor` | `assets.supplier.delete` | Delete a supplier subprocessor |
| `delete_supplier_type` | `assets.config.delete` | Delete a supplier type |
| `delete_supplier_type_requirement` | `assets.config.delete` | Delete a supplier type requirement |
| `delete_support_asset` | `assets.support_asset.delete` | Delete a support asset |
| `essential_asset_allowed_transitions` | `assets.essential_asset.read` | List the lifecycle transitions the caller may perform on a essential asset from its current state. |
| `get_asset_dependency` | `assets.dependency.read` | Get a asset dependency by ID |
| `get_asset_dependency_history` | `assets.dependency.read` | Return the change history of a asset dependency: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_asset_group` | `assets.group.read` | Get a asset group by ID |
| `get_asset_group_history` | `assets.group.read` | Return the change history of a asset group: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_asset_valuation` | `assets.essential_asset.read` | Get a asset valuation by ID |
| `get_asset_valuation_history` | `assets.essential_asset.read` | Return the change history of a asset valuation: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_certificate` | `assets.certificate.read` | Get a certificate by ID |
| `get_certificate_history` | `assets.certificate.read` | Return the change history of a certificate: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_contract` | `assets.contract.read` | Get a contract by ID |
| `get_contract_history` | `assets.contract.read` | Return the change history of a contract: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_essential_asset` | `assets.essential_asset.read` | Get a essential asset by ID |
| `get_essential_asset_history` | `assets.essential_asset.read` | Return the change history of a essential asset: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_site_asset_dependency` | `assets.dependency.read` | Get a site asset dependency by ID |
| `get_site_asset_dependency_history` | `assets.dependency.read` | Return the change history of a site asset dependency: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_site_supplier_dependency` | `assets.supplier_dependency.read` | Get a site supplier dependency by ID |
| `get_site_supplier_dependency_history` | `assets.supplier_dependency.read` | Return the change history of a site supplier dependency: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_supplier` | `assets.supplier.read` | Get a supplier by ID |
| `get_supplier_contact` | `assets.supplier.read` | Get a supplier contact by ID |
| `get_supplier_contact_history` | `assets.supplier.read` | Return the change history of a supplier contact: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_supplier_dependency` | `assets.supplier_dependency.read` | Get a supplier dependency by ID |
| `get_supplier_dependency_history` | `assets.supplier_dependency.read` | Return the change history of a supplier dependency: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_supplier_history` | `assets.supplier.read` | Return the change history of a supplier: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_supplier_requirement` | `assets.supplier.read` | Get a supplier requirement by ID |
| `get_supplier_requirement_review` | `assets.supplier.read` | Get a supplier requirement review by ID |
| `get_supplier_subprocessor` | `assets.supplier.read` | Get a supplier subprocessor by ID |
| `get_supplier_subprocessor_history` | `assets.supplier.read` | Return the change history of a supplier subprocessor: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_supplier_type` | `assets.config.read` | Get a supplier type by ID |
| `get_supplier_type_requirement` | `assets.config.read` | Get a supplier type requirement by ID |
| `get_support_asset` | `assets.support_asset.read` | Get a support asset by ID |
| `get_support_asset_history` | `assets.support_asset.read` | Return the change history of a support asset: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `list_asset_dependencys` | `assets.dependency.read` | List asset dependencys with optional search and filters |
| `list_asset_groups` | `assets.group.read` | List asset groups with optional search and filters |
| `list_asset_valuations` | `assets.essential_asset.read` | List asset valuations with optional search and filters |
| `list_certificates` | `assets.certificate.read` | List certificates with optional search and filters |
| `list_contracts` | `assets.contract.read` | List contracts with optional search and filters |
| `list_essential_assets` | `assets.essential_asset.read` | List essential assets with optional search and filters |
| `list_site_asset_dependencys` | `assets.dependency.read` | List site asset dependencys with optional search and filters |
| `list_site_supplier_dependencys` | `assets.supplier_dependency.read` | List site supplier dependencys with optional search and filters |
| `list_supplier_contacts` | `assets.supplier.read` | List supplier contacts with optional search and filters |
| `list_supplier_dependencys` | `assets.supplier_dependency.read` | List supplier dependencys with optional search and filters |
| `list_supplier_requirement_reviews` | `assets.supplier.read` | List supplier requirement reviews with optional search and filters |
| `list_supplier_requirements` | `assets.supplier.read` | List supplier requirements with optional search and filters |
| `list_supplier_subprocessors` | `assets.supplier.read` | List supplier subprocessors with optional search and filters |
| `list_supplier_type_requirements` | `assets.config.read` | List supplier type requirements with optional search and filters |
| `list_supplier_types` | `assets.config.read` | List supplier types with optional search and filters |
| `list_suppliers` | `assets.supplier.read` | List suppliers with optional search and filters |
| `list_support_assets` | `assets.support_asset.read` | List support assets with optional search and filters |
| `site_asset_dependency_allowed_transitions` | `assets.dependency.read` | List the lifecycle transitions the caller may perform on a site asset dependency from its current state. |
| `site_supplier_dependency_allowed_transitions` | `assets.supplier_dependency.read` | List the lifecycle transitions the caller may perform on a site supplier dependency from its current state. |
| `supplier_allowed_transitions` | `assets.supplier.read` | List the lifecycle transitions the caller may perform on a supplier from its current state. |
| `supplier_dependency_allowed_transitions` | `assets.supplier_dependency.read` | List the lifecycle transitions the caller may perform on a supplier dependency from its current state. |
| `support_asset_allowed_transitions` | `assets.support_asset.read` | List the lifecycle transitions the caller may perform on a support asset from its current state. |
| `transition_asset_dependency` | `assets.dependency.read` | Change the lifecycle state of a asset dependency (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_asset_group` | `assets.group.read` | Change the lifecycle state of a asset group (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_certificate` | `assets.certificate.read` | Change the lifecycle state of a certificate (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_contract` | `assets.contract.read` | Change the lifecycle state of a contract (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_essential_asset` | `assets.essential_asset.read` | Change the lifecycle state of a essential asset (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_site_asset_dependency` | `assets.dependency.read` | Change the lifecycle state of a site asset dependency (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_site_supplier_dependency` | `assets.supplier_dependency.read` | Change the lifecycle state of a site supplier dependency (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_supplier` | `assets.supplier.read` | Change the lifecycle state of a supplier (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_supplier_dependency` | `assets.supplier_dependency.read` | Change the lifecycle state of a supplier dependency (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_support_asset` | `assets.support_asset.read` | Change the lifecycle state of a support asset (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `update_asset_dependency` | `assets.dependency.update` | Update an existing asset dependency |
| `update_asset_group` | `assets.group.update` | Update an existing asset group |
| `update_asset_valuation` | `assets.essential_asset.update` | Update an existing asset valuation |
| `update_certificate` | `assets.certificate.update` | Update an existing certificate |
| `update_contract` | `assets.contract.update` | Update an existing contract |
| `update_essential_asset` | `assets.essential_asset.update` | Update an existing essential asset |
| `update_site_asset_dependency` | `assets.dependency.update` | Update an existing site asset dependency |
| `update_site_supplier_dependency` | `assets.supplier_dependency.update` | Update an existing site supplier dependency |
| `update_supplier` | `assets.supplier.update` | Update an existing supplier. Optionally provide 'image_url' (a public URL pointing to an image file) to set or replace the supplier logo. The image will be downloaded, resized to 128x128, and 64x64, 32x32, 16x16 variants will be generated automatically. Prefer 'image_url' over 'update_supplier_logo' when the logo is available as a URL. |
| `update_supplier_contact` | `assets.supplier.update` | Update an existing supplier contact |
| `update_supplier_dependency` | `assets.supplier_dependency.update` | Update an existing supplier dependency |
| `update_supplier_logo` | `assets.supplier.update` | Update a supplier's logo. Provide EITHER a base64 data URI via 'logo' OR a public image URL via 'image_url'. The image is resized to 128x128 and 64x64, 32x32, 16x16 variants are generated automatically. |
| `update_supplier_requirement` | `assets.supplier.update` | Update an existing supplier requirement |
| `update_supplier_requirement_review` | `assets.supplier.update` | Update an existing supplier requirement review |
| `update_supplier_subprocessor` | `assets.supplier.update` | Update an existing supplier subprocessor |
| `update_supplier_type` | `assets.config.update` | Update an existing supplier type |
| `update_supplier_type_requirement` | `assets.config.update` | Update an existing supplier type requirement |
| `update_support_asset` | `assets.support_asset.update` | Update an existing support asset |

## Compliance

| Tool | Permission | Description |
| --- | --- | --- |
| `action_plan_allowed_transitions` | `compliance.action_plan.read` | Get allowed status transitions for an action plan, including permission checks and refusal/cancellation flags. Call this before action_plan_transition to know what is possible. |
| `action_plan_kanban` | `compliance.action_plan.read` | Get action plans grouped by status for kanban board, including workflow transition rules |
| `action_plan_transition` | `compliance.action_plan.update` | Transition an action plan to a new Kanban status. Forward flow: new → to_define → to_validate → to_implement → implementation_to_validate → validated → closed. Refusals (require comment): to_validate → to_define, implementation_to_validate → to_implement. Cancellation: any non-terminal status → cancelled. |
| `action_plan_transitions` | `compliance.action_plan.read` | List transition history for an action plan |
| `batch_create_action_plans` | `compliance.action_plan.create` | Create or upsert multiple action plans in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_frameworks` | `compliance.framework.create` | Create or upsert multiple frameworks in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_requirement_mappings` | `compliance.mapping.create` | Create or upsert multiple requirement mappings in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_requirements` | `compliance.requirement.create` | Create or upsert multiple requirements in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_sections` | `compliance.section.create` | Create or upsert multiple sections in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `create_action_plan` | `compliance.action_plan.create` | Create a new action plan |
| `create_action_plan_comment` | `compliance.action_plan.update` | Create a comment or reply on an action plan |
| `create_assessment_result` | `compliance.assessment.create` | Create a new assessment result |
| `create_compliance_assessment` | `compliance.assessment.create` | Create a new compliance assessment |
| `create_finding` | `compliance.finding.create` | Create a new audit finding |
| `create_framework` | `compliance.framework.create` | Create a new framework |
| `create_requirement` | `compliance.requirement.create` | Create a new requirement |
| `create_requirement_mapping` | `compliance.mapping.create` | Create a new requirement mapping |
| `create_section` | `compliance.section.create` | Create a new section |
| `delete_action_plan` | `compliance.action_plan.delete` | Delete a action plan |
| `delete_assessment_result` | `compliance.assessment.delete` | Delete an assessment result |
| `delete_compliance_assessment` | `compliance.assessment.delete` | Delete a compliance assessment |
| `delete_finding` | `compliance.finding.delete` | Delete a finding |
| `delete_framework` | `compliance.framework.delete` | Delete a framework |
| `delete_requirement` | `compliance.requirement.delete` | Delete a requirement |
| `delete_requirement_mapping` | `compliance.mapping.delete` | Delete a requirement mapping |
| `delete_section` | `compliance.section.delete` | Delete a section |
| `framework_allowed_transitions` | `compliance.framework.read` | List the lifecycle transitions the caller may perform on a framework from its current state. |
| `get_action_plan` | `compliance.action_plan.read` | Get a action plan by ID |
| `get_action_plan_history` | `compliance.action_plan.read` | Return the change history of a action plan: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_assessment_result` | `compliance.assessment.read` | Get an assessment result by ID |
| `get_compliance_assessment` | `compliance.assessment.read` | Get a compliance assessment by ID |
| `get_finding` | `compliance.finding.read` | Get a finding by ID |
| `get_framework` | `compliance.framework.read` | Get a framework by ID |
| `get_framework_compliance_summary` | `compliance.framework.read` | Get compliance summary for a framework, including section-level compliance and status distribution |
| `get_framework_history` | `compliance.framework.read` | Return the change history of a framework: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_requirement` | `compliance.requirement.read` | Get a requirement by ID |
| `get_requirement_history` | `compliance.requirement.read` | Return the change history of a requirement: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_requirement_mapping` | `compliance.mapping.read` | Get a requirement mapping by ID |
| `get_requirement_mapping_history` | `compliance.mapping.read` | Return the change history of a requirement mapping: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_section` | `compliance.section.read` | Get a section by ID |
| `get_section_history` | `compliance.section.read` | Return the change history of a section: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `list_action_plan_comments` | `compliance.action_plan.read` | List comments on an action plan with threaded replies |
| `list_action_plans` | `compliance.action_plan.read` | List action plans with optional search and filters |
| `list_assessment_results` | `compliance.assessment.read` | List assessment results with optional search and filters |
| `list_compliance_assessments` | `compliance.assessment.read` | List compliance assessments with optional search and filters |
| `list_findings` | `compliance.finding.read` | List findings with optional search and filters |
| `list_frameworks` | `compliance.framework.read` | List frameworks with optional search and filters |
| `list_requirement_mappings` | `compliance.mapping.read` | List requirement mappings with optional search and filters |
| `list_requirement_risks` | `compliance.requirement.read` | List all risks linked to a compliance requirement. Returns risk id, reference, name, current_risk_level, priority and status for each linked risk. |
| `list_requirements` | `compliance.requirement.read` | List requirements with optional search and filters |
| `list_sections` | `compliance.section.read` | List sections with optional search and filters |
| `requirement_allowed_transitions` | `compliance.requirement.read` | List the lifecycle transitions the caller may perform on a requirement from its current state. |
| `semantic_search_requirements` | `compliance.requirement.read` | Find framework requirements / controls by MEANING using embeddings (language-agnostic). Use for conceptual / topic questions when an exact reference is not given. Read-only; requires the semantic index to be built (AI_ASSISTANT_SEMANTIC_ENABLED). |
| `transition_action_plan` | `compliance.action_plan.read` | Change the lifecycle state of a action plan (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_framework` | `compliance.framework.read` | Change the lifecycle state of a framework (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_requirement` | `compliance.requirement.read` | Change the lifecycle state of a requirement (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `update_action_plan` | `compliance.action_plan.update` | Update an existing action plan |
| `update_assessment_result` | `compliance.assessment.update` | Update an existing assessment result |
| `update_compliance_assessment` | `compliance.assessment.update` | Update an existing compliance assessment |
| `update_finding` | `compliance.finding.update` | Update an existing audit finding |
| `update_framework` | `compliance.framework.update` | Update an existing framework |
| `update_requirement` | `compliance.requirement.update` | Update an existing requirement |
| `update_requirement_mapping` | `compliance.mapping.update` | Update an existing requirement mapping |
| `update_section` | `compliance.section.update` | Update an existing section |

## Governance and context

| Tool | Permission | Description |
| --- | --- | --- |
| `activity_allowed_transitions` | `context.activity.read` | List the lifecycle transitions the caller may perform on a activity from its current state. |
| `batch_create_activitys` | `context.activity.create` | Create or upsert multiple activitys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_expectations` | `context.expectation.create` | Create or upsert multiple expectations in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_indicator_measurements` | `context.indicator.create` | Create or upsert multiple indicator measurements in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_indicators` | `context.indicator.create` | Create or upsert multiple indicators in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_issues` | `context.issue.create` | Create or upsert multiple issues in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_objectives` | `context.objective.create` | Create or upsert multiple objectives in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_responsibilitys` | `context.role.create` | Create or upsert multiple responsibilitys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_roles` | `context.role.create` | Create or upsert multiple roles in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_scopes` | `context.scope.create` | Create or upsert multiple scopes in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_sites` | `context.site.create` | Create or upsert multiple sites in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_stakeholders` | `context.stakeholder.create` | Create or upsert multiple stakeholders in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_swot_analysiss` | `context.swot.create` | Create or upsert multiple swot analysiss in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_swot_items` | `context.swot.create` | Create or upsert multiple swot items in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_swot_strategys` | `context.swot.create` | Create or upsert multiple swot strategys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `create_activity` | `context.activity.create` | Create a new activity |
| `create_expectation` | `context.expectation.create` | Create a new expectation |
| `create_indicator` | `context.indicator.create` | Create a new indicator |
| `create_indicator_measurement` | `context.indicator.create` | Create a new indicator measurement |
| `create_issue` | `context.issue.create` | Create a new issue |
| `create_objective` | `context.objective.create` | Create a new objective |
| `create_responsibility` | `context.role.create` | Create a new responsibility |
| `create_role` | `context.role.create` | Create a new role |
| `create_scope` | `context.scope.create` | Create a new scope |
| `create_site` | `context.site.create` | Create a new site |
| `create_stakeholder` | `context.stakeholder.create` | Create a new stakeholder |
| `create_stakeholder_feedback` | `context.stakeholder_feedback.create` | Record formal feedback from an interested party (ISO 27001:2022 clause 9.3.2.e). |
| `create_swot_analysis` | `context.swot.create` | Create a new swot analysis |
| `create_swot_item` | `context.swot.create` | Create a new swot item |
| `create_swot_strategy` | `context.swot.create` | Create a new swot strategy |
| `create_tag` | `context.scope.create` | Create a tag |
| `delete_activity` | `context.activity.delete` | Delete a activity |
| `delete_expectation` | `context.expectation.delete` | Delete a expectation |
| `delete_indicator` | `context.indicator.delete` | Delete a indicator |
| `delete_indicator_measurement` | `context.indicator.delete` | Delete a indicator measurement |
| `delete_issue` | `context.issue.delete` | Delete a issue |
| `delete_objective` | `context.objective.delete` | Delete a objective |
| `delete_responsibility` | `context.role.delete` | Delete a responsibility |
| `delete_role` | `context.role.delete` | Delete a role |
| `delete_scope` | `context.scope.delete` | Delete a scope |
| `delete_site` | `context.site.delete` | Delete a site |
| `delete_stakeholder` | `context.stakeholder.delete` | Delete a stakeholder |
| `delete_swot_analysis` | `context.swot.delete` | Delete a swot analysis |
| `delete_swot_item` | `context.swot.delete` | Delete a swot item |
| `delete_swot_strategy` | `context.swot.delete` | Delete a swot strategy |
| `delete_tag` | `context.scope.delete` | Delete a tag |
| `expectation_allowed_transitions` | `context.expectation.read` | List the lifecycle transitions the caller may perform on a expectation from its current state. |
| `get_activity` | `context.activity.read` | Get a activity by ID |
| `get_activity_history` | `context.activity.read` | Return the change history of a activity: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_expectation` | `context.expectation.read` | Get a expectation by ID |
| `get_expectation_history` | `context.expectation.read` | Return the change history of a expectation: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_indicator` | `context.indicator.read` | Get a indicator by ID |
| `get_indicator_history` | `context.indicator.read` | Return the change history of a indicator: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_indicator_measurement` | `context.indicator.read` | Get a indicator measurement by ID |
| `get_issue` | `context.issue.read` | Get a issue by ID |
| `get_issue_history` | `context.issue.read` | Return the change history of a issue: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_objective` | `context.objective.read` | Get a objective by ID |
| `get_objective_history` | `context.objective.read` | Return the change history of a objective: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_responsibility` | `context.role.read` | Get a responsibility by ID |
| `get_responsibility_history` | `context.role.read` | Return the change history of a responsibility: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_role` | `context.role.read` | Get a role by ID |
| `get_role_history` | `context.role.read` | Return the change history of a role: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_scope` | `context.scope.read` | Get a scope by ID |
| `get_scope_history` | `context.scope.read` | Return the change history of a scope: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_site` | `context.site.read` | Get a site by ID |
| `get_site_history` | `context.site.read` | Return the change history of a site: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_stakeholder` | `context.stakeholder.read` | Get a stakeholder by ID |
| `get_stakeholder_history` | `context.stakeholder.read` | Return the change history of a stakeholder: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_swot_analysis` | `context.swot.read` | Get a swot analysis by ID |
| `get_swot_analysis_history` | `context.swot.read` | Return the change history of a swot analysis: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_swot_item` | `context.swot.read` | Get a swot item by ID |
| `get_swot_item_history` | `context.swot.read` | Return the change history of a swot item: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_swot_strategy` | `context.swot.read` | Get a swot strategy by ID |
| `get_swot_strategy_history` | `context.swot.read` | Return the change history of a swot strategy: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `indicator_allowed_transitions` | `context.indicator.read` | List the lifecycle transitions the caller may perform on a indicator from its current state. |
| `issue_allowed_transitions` | `context.issue.read` | List the lifecycle transitions the caller may perform on a issue from its current state. |
| `list_activitys` | `context.activity.read` | List activitys with optional search and filters |
| `list_expectations` | `context.expectation.read` | List expectations with optional search and filters |
| `list_indicator_measurements` | `context.indicator.read` | List indicator measurements with optional search and filters |
| `list_indicators` | `context.indicator.read` | List indicators with optional search and filters |
| `list_issues` | `context.issue.read` | List issues with optional search and filters |
| `list_objectives` | `context.objective.read` | List objectives with optional search and filters |
| `list_responsibilitys` | `context.role.read` | List responsibilitys with optional search and filters |
| `list_roles` | `context.role.read` | List roles with optional search and filters |
| `list_scopes` | `context.scope.read` | List scopes with optional search and filters |
| `list_sites` | `context.site.read` | List sites with optional search and filters |
| `list_stakeholder_feedback` | `context.stakeholder_feedback.read` | List formal stakeholder feedback (ISO 27001:2022 clause 9.3.2.e). |
| `list_stakeholders` | `context.stakeholder.read` | List stakeholders with optional search and filters |
| `list_swot_analysiss` | `context.swot.read` | List swot analysiss with optional search and filters |
| `list_swot_items` | `context.swot.read` | List swot items with optional search and filters |
| `list_swot_strategys` | `context.swot.read` | List swot strategys with optional search and filters |
| `list_tags` | `context.scope.read` | List all tags |
| `objective_allowed_transitions` | `context.objective.read` | List the lifecycle transitions the caller may perform on a objective from its current state. |
| `role_allowed_transitions` | `context.role.read` | List the lifecycle transitions the caller may perform on a role from its current state. |
| `scope_allowed_transitions` | `context.scope.read` | List the lifecycle transitions the caller may perform on a scope from its current state. |
| `site_allowed_transitions` | `context.site.read` | List the lifecycle transitions the caller may perform on a site from its current state. |
| `stakeholder_allowed_transitions` | `context.stakeholder.read` | List the lifecycle transitions the caller may perform on a stakeholder from its current state. |
| `swot_analysis_allowed_transitions` | `context.swot.read` | List the lifecycle transitions the caller may perform on a swot analysis from its current state. |
| `swot_item_allowed_transitions` | `context.swot.read` | List the lifecycle transitions the caller may perform on a swot item from its current state. |
| `swot_strategy_allowed_transitions` | `context.swot.read` | List the lifecycle transitions the caller may perform on a swot strategy from its current state. |
| `transition_activity` | `context.activity.read` | Change the lifecycle state of a activity (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_expectation` | `context.expectation.read` | Change the lifecycle state of a expectation (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_indicator` | `context.indicator.read` | Change the lifecycle state of a indicator (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_issue` | `context.issue.read` | Change the lifecycle state of a issue (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_objective` | `context.objective.read` | Change the lifecycle state of a objective (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_role` | `context.role.read` | Change the lifecycle state of a role (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_scope` | `context.scope.read` | Change the lifecycle state of a scope (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_site` | `context.site.read` | Change the lifecycle state of a site (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_stakeholder` | `context.stakeholder.read` | Change the lifecycle state of a stakeholder (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_swot_analysis` | `context.swot.read` | Change the lifecycle state of a swot analysis (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_swot_item` | `context.swot.read` | Change the lifecycle state of a swot item (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_swot_strategy` | `context.swot.read` | Change the lifecycle state of a swot strategy (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `update_activity` | `context.activity.update` | Update an existing activity |
| `update_expectation` | `context.expectation.update` | Update an existing expectation |
| `update_indicator` | `context.indicator.update` | Update an existing indicator |
| `update_indicator_measurement` | `context.indicator.update` | Update an existing indicator measurement |
| `update_issue` | `context.issue.update` | Update an existing issue |
| `update_objective` | `context.objective.update` | Update an existing objective |
| `update_responsibility` | `context.role.update` | Update an existing responsibility |
| `update_role` | `context.role.update` | Update an existing role |
| `update_scope` | `context.scope.update` | Update an existing scope |
| `update_site` | `context.site.update` | Update an existing site |
| `update_stakeholder` | `context.stakeholder.update` | Update an existing stakeholder |
| `update_swot_analysis` | `context.swot.update` | Update an existing swot analysis |
| `update_swot_item` | `context.swot.update` | Update an existing swot item |
| `update_swot_strategy` | `context.swot.update` | Update an existing swot strategy |

## General

| Tool | Permission | Description |
| --- | --- | --- |
| `ask_assistant` | - | Ask Cairn's natural-language assistant a read-only question about GRC data (e.g. 'Which decisions were made at the last management review?'). Requires the optional AI assistant to be enabled (AI_ASSISTANT_ENABLED). The answer cites real records; data access enforces the caller's permissions. |
| `create_saved_filter` | - | Save a named list filter for the current user. `query` is the list's filter query string; `view_key` is the list key (e.g. context.issue). |
| `delete_saved_filter` | - | Delete one of the current user's saved list filters by id. |
| `get_dashboard_layout` | - | Get the currently authenticated user's home-dashboard widget layout (ordered list of {key, id, size, visible, zone, params}) and the catalogue of available widgets with their allowed sizes. `id` is the widget type and `key` is the per-instance id. A size is a 'WxH' tile token: width W in 1..4 quarter-columns (1=1/4 .. 4=full width) by height H in 1..4 fixed row units, e.g. '2x1' or '4x2'. A widget with `multiple: true` (e.g. 'indicator') can appear several times, each instance carrying its own `params` (the indicator widget takes `{indicator: <id>, show_chart: bool}`). |
| `get_me` | - | Get information about the currently authenticated user, including capability flags: 'can_override_import_dates' (may set created_at / updated_at on import) and 'can_create_users'. |
| `help` | - | Get usage documentation for the Cairn MCP server. Call without arguments for the full guide, or with a topic for focused help. Topics: context, assets, compliance, risks, incidents, batch, workflow, permissions, examples, users |
| `kanban_board` | - | Get the unified To do / Doing / Done board aggregating action plans, treatment actions, audits and risk assessments (read-only) |
| `list_dependencies` | - | List the third-party open source components this Cairn instance is built on : name, resolved version, official repository URL and what each one is used for. Same registry as the About modal. Optionally filtered by group. |
| `list_notifications` | - | List the currently authenticated user's in-app notifications (most recent first), with the unread count. Set unread_only=true to only return unread notifications. |
| `list_saved_filters` | - | List the current user's saved list filters (own + shared). Optional view_key (e.g. 'context.issue') narrows to one list. |
| `mark_all_notifications_read` | - | Mark all of the authenticated user's unread notifications as read. |
| `mark_notification_read` | - | Mark one of the authenticated user's notifications as read. |
| `update_dashboard_layout` | - | Replace the currently authenticated user's home-dashboard widget layout. Pass `layout` as an ordered list of {key, id, size, visible, zone, params} instances; use get_dashboard_layout first to discover widget ids, allowed sizes and which widgets are 'multiple'. Give each instance of a 'multiple' widget a distinct key. The payload is sanitised against the registry. |
| `update_me` | - | Update the currently authenticated user's profile (self-service). Accepts first_name, last_name, phone, language, timezone, theme_preference. |

## Incidents

| Tool | Permission | Description |
| --- | --- | --- |
| `batch_create_incident_evidences` | `incidents.evidence.create` | Create or upsert multiple incident evidences in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_incident_notifications` | `incidents.notification.create` | Create or upsert multiple incident notifications in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_incident_response_actions` | `incidents.incident.create` | Create or upsert multiple incident response actions in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_incident_response_plans` | `incidents.response_plan.create` | Create or upsert multiple incident response plans in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_incidents` | `incidents.incident.create` | Create or upsert multiple incidents in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_obligation_templates` | `incidents.response_plan.create` | Create or upsert multiple obligation templates in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_personal_data_breachs` | `incidents.notification.create` | Create or upsert multiple personal data breachs in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_post_incident_reviews` | `incidents.review.create` | Create or upsert multiple post incident reviews in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_reporting_authoritys` | `incidents.response_plan.create` | Create or upsert multiple reporting authoritys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_security_events` | `incidents.event.create` | Create or upsert multiple security events in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `create_evidence_custody_event` | `incidents.evidence.update` | Record one handling act on an evidence item. The chain of custody is append-only: there is no update and no delete tool, and a mistake is corrected by appending a further act that states what the earlier one got wrong. The actor is always the calling account and the source is always 'manual'. Do not use this to assert an integrity verdict: call verify_evidence_integrity, which measures the artefact itself. |
| `create_incident` | `incidents.incident.create` | Create a new incident |
| `create_incident_evidence` | `incidents.evidence.create` | Create a new incident evidence |
| `create_incident_notification` | `incidents.notification.create` | Create a new incident notification |
| `create_incident_response_action` | `incidents.incident.create` | Create a new incident response action |
| `create_incident_response_plan` | `incidents.response_plan.create` | Create a new incident response plan |
| `create_incident_timeline_entry` | `incidents.incident.create` | Append one entry to an incident's chronology. The chronology is append-only: there is no update and no delete tool. A mistake is corrected by appending a further entry of type 'correction' that names the entry it supersedes and states why. The author is always the calling account and the source is always 'manual'. |
| `create_notification_filing` | `incidents.notification.update` | Record that a notification obligation was actually transmitted. The filing log is append-only: there is no update and no delete tool, and an amendment is a further filing, never a rewrite. The first filing on an obligation runs through the lifecycle and freezes its lateness verdict; later filings insert without disturbing it. The submitter is always the calling account. |
| `create_obligation_template` | `incidents.response_plan.create` | Create a new obligation template |
| `create_personal_data_breach` | `incidents.notification.create` | Create a new personal data breach |
| `create_post_incident_review` | `incidents.review.create` | Create a new post incident review |
| `create_reporting_authority` | `incidents.response_plan.create` | Create a new reporting authority |
| `create_security_event` | `incidents.event.create` | Create a new security event |
| `declare_incident_from_event` | `incidents.event.validate` | Promote an assessed security event into an incident, as one atomic act. Creates the incident in draft, carries over the event's title, description, detection source, timestamps, reporter, scopes and affected assets, declares it through its lifecycle, links the event to it and moves the event to its confirmed-incident step. Requires both incidents.event.validate (via the transition) and incidents.incident.create. The event must be under assessment. Optional arguments override the values carried across. |
| `delete_incident` | `incidents.incident.delete` | Delete a incident |
| `delete_incident_evidence` | `incidents.evidence.delete` | Delete a incident evidence |
| `delete_incident_notification` | `incidents.notification.delete` | Delete a incident notification |
| `delete_incident_response_action` | `incidents.incident.delete` | Delete a incident response action |
| `delete_incident_response_plan` | `incidents.response_plan.delete` | Delete a incident response plan |
| `delete_obligation_template` | `incidents.response_plan.delete` | Delete a obligation template |
| `delete_personal_data_breach` | `incidents.notification.delete` | Delete a personal data breach |
| `delete_post_incident_review` | `incidents.review.delete` | Delete a post incident review |
| `delete_reporting_authority` | `incidents.response_plan.delete` | Delete a reporting authority |
| `delete_security_event` | `incidents.event.delete` | Delete a security event |
| `get_evidence_custody_event` | `incidents.evidence.read` | Get a evidence custody event by ID |
| `get_evidence_custody_event_history` | `incidents.evidence.read` | Return the change history of a evidence custody event. On an append-only ledger this is the tamper-detection surface: a row whose trail shows more writes than the design allows has been altered outside the supported paths. |
| `get_incident` | `incidents.incident.read` | Get a incident by ID |
| `get_incident_evidence` | `incidents.evidence.read` | Get a incident evidence by ID |
| `get_incident_evidence_history` | `incidents.evidence.read` | Return the change history of a incident evidence: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_incident_history` | `incidents.incident.read` | Return the change history of a incident: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_incident_notification` | `incidents.notification.read` | Get a incident notification by ID |
| `get_incident_notification_history` | `incidents.notification.read` | Return the change history of a incident notification: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_incident_response_action` | `incidents.incident.read` | Get a incident response action by ID |
| `get_incident_response_action_history` | `incidents.incident.read` | Return the change history of a incident response action: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_incident_response_plan` | `incidents.response_plan.read` | Get a incident response plan by ID |
| `get_incident_response_plan_history` | `incidents.response_plan.read` | Return the change history of a incident response plan: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_incident_timeline_entry` | `incidents.incident.read` | Get a incident timeline entry by ID |
| `get_incident_timeline_entry_history` | `incidents.incident.read` | Return the change history of a incident timeline entry. On an append-only ledger this is the tamper-detection surface: a row whose trail shows more writes than the design allows has been altered outside the supported paths. |
| `get_notification_filing` | `incidents.notification.read` | Get a notification filing by ID |
| `get_notification_filing_history` | `incidents.notification.read` | Return the change history of a notification filing. On an append-only ledger this is the tamper-detection surface: a row whose trail shows more writes than the design allows has been altered outside the supported paths. |
| `get_obligation_template` | `incidents.response_plan.read` | Get a obligation template by ID |
| `get_obligation_template_history` | `incidents.response_plan.read` | Return the change history of a obligation template: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_personal_data_breach` | `incidents.notification.read` | Get a personal data breach by ID |
| `get_personal_data_breach_history` | `incidents.notification.read` | Return the change history of a personal data breach: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_post_incident_review` | `incidents.review.read` | Get a post incident review by ID |
| `get_post_incident_review_history` | `incidents.review.read` | Return the change history of a post incident review: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_reporting_authority` | `incidents.response_plan.read` | Get a reporting authority by ID |
| `get_reporting_authority_history` | `incidents.response_plan.read` | Return the change history of a reporting authority: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_security_event` | `incidents.event.read` | Get a security event by ID |
| `get_security_event_history` | `incidents.event.read` | Return the change history of a security event: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `incident_allowed_transitions` | `incidents.incident.read` | List the lifecycle transitions the caller may perform on a incident from its current state. |
| `incident_evidence_allowed_transitions` | `incidents.evidence.read` | List the lifecycle transitions the caller may perform on a incident evidence from its current state. |
| `incident_notification_allowed_transitions` | `incidents.notification.read` | List the lifecycle transitions the caller may perform on a incident notification from its current state. |
| `incident_response_plan_allowed_transitions` | `incidents.response_plan.read` | List the lifecycle transitions the caller may perform on a incident response plan from its current state. |
| `list_evidence_custody_events` | `incidents.evidence.read` | List evidence custody events with optional search and filters. Append-only ledger: there is no update or delete tool for it. |
| `list_incident_evidences` | `incidents.evidence.read` | List incident evidences with optional search and filters |
| `list_incident_notifications` | `incidents.notification.read` | List incident notifications with optional search and filters |
| `list_incident_response_actions` | `incidents.incident.read` | List incident response actions with optional search and filters |
| `list_incident_response_plans` | `incidents.response_plan.read` | List incident response plans with optional search and filters |
| `list_incident_timeline_entries` | `incidents.incident.read` | List incident timeline entrys with optional search and filters. Append-only ledger: there is no update or delete tool for it. |
| `list_incidents` | `incidents.incident.read` | List incidents with optional search and filters |
| `list_notification_filings` | `incidents.notification.read` | List notification filings with optional search and filters. Append-only ledger: there is no update or delete tool for it. |
| `list_obligation_templates` | `incidents.response_plan.read` | List obligation templates with optional search and filters |
| `list_overdue_incident_notifications` | `incidents.notification.read` | List every notification obligation whose statutory deadline has passed with no filing recorded: the 'are we late' question answered in one call. Returns the obligation, its regime and recipient, the deadline, how many hours it is overdue, and the incident it belongs to with its manager. Obligations with no deadline, already filed, or in a terminal step are excluded. |
| `list_personal_data_breachs` | `incidents.notification.read` | List personal data breachs with optional search and filters |
| `list_post_incident_reviews` | `incidents.review.read` | List post incident reviews with optional search and filters |
| `list_reporting_authoritys` | `incidents.response_plan.read` | List reporting authoritys with optional search and filters |
| `list_security_events` | `incidents.event.read` | List security events with optional search and filters |
| `obligation_template_allowed_transitions` | `incidents.response_plan.read` | List the lifecycle transitions the caller may perform on a obligation template from its current state. |
| `personal_data_breach_allowed_transitions` | `incidents.notification.read` | List the lifecycle transitions the caller may perform on a personal data breach from its current state. |
| `post_incident_review_allowed_transitions` | `incidents.review.read` | List the lifecycle transitions the caller may perform on a post incident review from its current state. |
| `reporting_authority_allowed_transitions` | `incidents.response_plan.read` | List the lifecycle transitions the caller may perform on a reporting authority from its current state. |
| `security_event_allowed_transitions` | `incidents.event.read` | List the lifecycle transitions the caller may perform on a security event from its current state. |
| `transition_incident` | `incidents.incident.read` | Change the lifecycle state of a incident (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_incident_evidence` | `incidents.evidence.read` | Change the lifecycle state of a incident evidence (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_incident_notification` | `incidents.notification.read` | Change the lifecycle state of a incident notification (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_incident_response_plan` | `incidents.response_plan.read` | Change the lifecycle state of a incident response plan (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_obligation_template` | `incidents.response_plan.read` | Change the lifecycle state of a obligation template (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_personal_data_breach` | `incidents.notification.read` | Change the lifecycle state of a personal data breach (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_post_incident_review` | `incidents.review.read` | Change the lifecycle state of a post incident review (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_reporting_authority` | `incidents.response_plan.read` | Change the lifecycle state of a reporting authority (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_security_event` | `incidents.event.read` | Change the lifecycle state of a security event (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `update_incident` | `incidents.incident.update` | Update an existing incident |
| `update_incident_evidence` | `incidents.evidence.update` | Update an existing incident evidence |
| `update_incident_notification` | `incidents.notification.update` | Update an existing incident notification |
| `update_incident_response_action` | `incidents.incident.update` | Update an existing incident response action |
| `update_incident_response_plan` | `incidents.response_plan.update` | Update an existing incident response plan |
| `update_obligation_template` | `incidents.response_plan.update` | Update an existing obligation template |
| `update_personal_data_breach` | `incidents.notification.update` | Update an existing personal data breach |
| `update_post_incident_review` | `incidents.review.update` | Update an existing post incident review |
| `update_reporting_authority` | `incidents.response_plan.update` | Update an existing reporting authority |
| `update_security_event` | `incidents.event.update` | Update an existing security event |
| `verify_evidence_integrity` | `incidents.evidence.update` | Re-measure an evidence artefact and append the result to its chain of custody. Returns one of three outcomes, which are never collapsed into each other: 'match' (the artefact was read and its digest equals the recorded content hash), 'mismatch' (it was read and the digest differs, which is a permanent chain-of-custody break) and 'not_verifiable' (the item is registered by reference, or the file is missing or unreadable, which is a claim about the storage and not about the artefact). The digest is measured, never asserted by the caller. |

## Reports and management review

| Tool | Permission | Description |
| --- | --- | --- |
| `create_isms_change` | `reports.management_review.update` | Record an ISMS change decided during a management review. |
| `create_management_review` | `reports.management_review.create` | Create a management review (ISO 27001:2022 clause 9.3). |
| `create_management_review_decision` | `reports.management_review.update` | Record a decision from a management review (ISO 27001:2022 clause 9.3.3). |
| `delete_report` | `reports.report.delete` | Delete a generated report |
| `download_report` | `reports.report.read` | Retrieve the binary content of a previously generated report. Returns the file as a base64-encoded string along with its content type, size and original filename. Use list_reports first to discover available report IDs. |
| `export_management_review` | `reports.management_review.read` | Export a management review as DOCX (meeting minutes) or PPTX (presentation). Returns base64-encoded content. |
| `generate_audit_report` | `reports.report.create` | Generate an audit report PDF for a completed or closed compliance assessment |
| `generate_management_review_docx` | `reports.report.create` | Generate a management review meeting minutes document (Word) covering ISO 27001 clause 9.3 inputs: action plans, issues, stakeholders, security performance, risks, and improvement opportunities |
| `generate_management_review_pptx` | `reports.report.create` | Generate a management review presentation (PowerPoint) covering ISO 27001 clause 9.3 inputs: action plans, issues, stakeholders, security performance, risks, and improvement opportunities |
| `generate_soa_report` | `reports.report.create` | Generate a Statement of Applicability (SoA) PDF report for one or more frameworks |
| `get_management_review` | `reports.management_review.read` | Get a management review by ID. |
| `list_isms_changes` | `reports.management_review.read` | List ISMS changes decided during management reviews (ISO 27001:2022 clause 9.3.3). |
| `list_management_review_decisions` | `reports.management_review.read` | List decisions (ISO 27001:2022 clause 9.3.3 outputs). Filter by review or status. |
| `list_management_reviews` | `reports.management_review.read` | List management reviews (ISO 27001:2022 clause 9.3). Filter by status or scope. |
| `list_reports` | `reports.report.read` | List generated reports, optionally filtered by report_type |
| `promote_decision_to_action_plan` | `reports.management_review.update` | Create a ComplianceActionPlan from a management review decision. |
| `set_participant_signature` | `reports.management_review.update` | Attach a graphical signature (data URI) to a participant for DOCX embedding. |
| `transition_management_review` | `reports.management_review.update` | Transition a management review to a new status (planned -> in_preparation -> held -> closed, or cancelled). |

## Risks

| Tool | Permission | Description |
| --- | --- | --- |
| `batch_create_ebios_attack_path_steps` | `risks.ebios_strategic.create` | Create or upsert multiple ebios attack path steps in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_attack_techniques` | `risks.ebios_operational.create` | Create or upsert multiple ebios attack techniques in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_baseline_gaps` | `risks.ebios_baseline.create` | Create or upsert multiple ebios baseline gaps in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_ecosystem_stakeholders` | `risks.ebios_ecosystem.create` | Create or upsert multiple ebios ecosystem stakeholders in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_feared_events` | `risks.ebios_baseline.create` | Create or upsert multiple ebios feared events in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_operational_scenarios` | `risks.ebios_operational.create` | Create or upsert multiple ebios operational scenarios in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_pacs_measures` | `risks.ebios_summary.create` | Create or upsert multiple ebios pacs measures in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_risk_sources` | `risks.ebios_risk_source.create` | Create or upsert multiple ebios risk sources in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_security_baselines` | `risks.ebios_baseline.create` | Create or upsert multiple ebios security baselines in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_sr_ov_pairs` | `risks.ebios_risk_source.create` | Create or upsert multiple ebios sr ov pairs in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_strategic_scenarios` | `risks.ebios_strategic.create` | Create or upsert multiple ebios strategic scenarios in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_study_frameworks` | `risks.ebios_assessment.create` | Create or upsert multiple ebios study frameworks in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_summarys` | `risks.ebios_summary.create` | Create or upsert multiple ebios summarys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_targeted_objectives` | `risks.ebios_risk_source.create` | Create or upsert multiple ebios targeted objectives in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_ebios_workshops` | `risks.ebios_assessment.create` | Create or upsert multiple ebios workshops in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_iso27005_risks` | `risks.iso27005.create` | Create or upsert multiple iso27005 risks in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_risk_acceptances` | `risks.acceptance.create` | Create or upsert multiple risk acceptances in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_risk_assessments` | `risks.assessment.create` | Create or upsert multiple risk assessments in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_risk_criterias` | `risks.criteria.create` | Create or upsert multiple risk criterias in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_risk_levels` | `risks.criteria.create` | Create or upsert multiple risk levels in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_risk_treatment_plans` | `risks.treatment.create` | Create or upsert multiple risk treatment plans in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_risks` | `risks.risk.create` | Create or upsert multiple risks in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_scale_levels` | `risks.criteria.create` | Create or upsert multiple scale levels in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_threats` | `risks.threat.create` | Create or upsert multiple threats in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_treatment_actions` | `risks.treatment.create` | Create or upsert multiple treatment actions in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_vulnerabilitys` | `risks.vulnerability.create` | Create or upsert multiple vulnerabilitys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `capture_ebios_risk_mappings` | `risks.ebios_summary.update` | Snapshot the assessment's risk register into the EbiosSummary before / after JSON slots so the cartography can render the treatment effect. Pass capture_before / capture_after to scope the update; both default to true. |
| `consolidate_ebios_operational_scenario_to_risk` | `risks.risk.create` | Materialise an EBIOS operational scenario into a Risk in the unified register. Idempotent: returns the existing Risk if the scenario has already been consolidated. |
| `consolidate_iso27005_risk` | `risks.risk.create` | Materialise an ISO 27005 analysis (threat × vulnerability) into a Risk in the unified register. Idempotent: returns the existing Risk if the analysis has already been consolidated. The source link is preserved via source_entity_id / source_entity_type on the resulting Risk. |
| `create_ebios_attack_path_step` | `risks.ebios_strategic.create` | Create a new ebios attack path step |
| `create_ebios_attack_technique` | `risks.ebios_operational.create` | Create a new ebios attack technique |
| `create_ebios_baseline_gap` | `risks.ebios_baseline.create` | Create a new ebios baseline gap |
| `create_ebios_ecosystem_stakeholder` | `risks.ebios_ecosystem.create` | Create a new ebios ecosystem stakeholder |
| `create_ebios_feared_event` | `risks.ebios_baseline.create` | Create a new ebios feared event |
| `create_ebios_operational_scenario` | `risks.ebios_operational.create` | Create a new ebios operational scenario |
| `create_ebios_pacs_measure` | `risks.ebios_summary.create` | Create a new ebios pacs measure |
| `create_ebios_risk_source` | `risks.ebios_risk_source.create` | Create a new ebios risk source |
| `create_ebios_security_baseline` | `risks.ebios_baseline.create` | Create a new ebios security baseline |
| `create_ebios_sr_ov_pair` | `risks.ebios_risk_source.create` | Create a new ebios sr ov pair |
| `create_ebios_strategic_scenario` | `risks.ebios_strategic.create` | Create a new ebios strategic scenario |
| `create_ebios_study_framework` | `risks.ebios_assessment.create` | Create a new ebios study framework |
| `create_ebios_summary` | `risks.ebios_summary.create` | Create a new ebios summary |
| `create_ebios_targeted_objective` | `risks.ebios_risk_source.create` | Create a new ebios targeted objective |
| `create_ebios_workshop` | `risks.ebios_assessment.create` | Create a new ebios workshop |
| `create_iso27005_risk` | `risks.iso27005.create` | Create a new iso27005 risk |
| `create_risk` | `risks.risk.create` | Create a new risk |
| `create_risk_acceptance` | `risks.acceptance.create` | Create a new risk acceptance |
| `create_risk_assessment` | `risks.assessment.create` | Create a new risk assessment |
| `create_risk_criteria` | `risks.criteria.create` | Create a new risk criteria |
| `create_risk_level` | `risks.criteria.create` | Create a new risk level |
| `create_risk_treatment_plan` | `risks.treatment.create` | Create a new risk treatment plan |
| `create_scale_level` | `risks.criteria.create` | Create a new scale level |
| `create_threat` | `risks.threat.create` | Create a new threat |
| `create_treatment_action` | `risks.treatment.create` | Create a new treatment action |
| `create_vulnerability` | `risks.vulnerability.create` | Create a new vulnerability |
| `delete_ebios_attack_path_step` | `risks.ebios_strategic.delete` | Delete a ebios attack path step |
| `delete_ebios_attack_technique` | `risks.ebios_operational.delete` | Delete a ebios attack technique |
| `delete_ebios_baseline_gap` | `risks.ebios_baseline.delete` | Delete a ebios baseline gap |
| `delete_ebios_ecosystem_stakeholder` | `risks.ebios_ecosystem.delete` | Delete a ebios ecosystem stakeholder |
| `delete_ebios_feared_event` | `risks.ebios_baseline.delete` | Delete a ebios feared event |
| `delete_ebios_operational_scenario` | `risks.ebios_operational.delete` | Delete a ebios operational scenario |
| `delete_ebios_pacs_measure` | `risks.ebios_summary.delete` | Delete a ebios pacs measure |
| `delete_ebios_risk_source` | `risks.ebios_risk_source.delete` | Delete a ebios risk source |
| `delete_ebios_security_baseline` | `risks.ebios_baseline.delete` | Delete a ebios security baseline |
| `delete_ebios_sr_ov_pair` | `risks.ebios_risk_source.delete` | Delete a ebios sr ov pair |
| `delete_ebios_strategic_scenario` | `risks.ebios_strategic.delete` | Delete a ebios strategic scenario |
| `delete_ebios_study_framework` | `risks.ebios_assessment.delete` | Delete a ebios study framework |
| `delete_ebios_summary` | `risks.ebios_summary.delete` | Delete a ebios summary |
| `delete_ebios_targeted_objective` | `risks.ebios_risk_source.delete` | Delete a ebios targeted objective |
| `delete_ebios_workshop` | `risks.ebios_assessment.delete` | Delete a ebios workshop |
| `delete_iso27005_risk` | `risks.iso27005.delete` | Delete a iso27005 risk |
| `delete_risk` | `risks.risk.delete` | Delete a risk |
| `delete_risk_acceptance` | `risks.acceptance.delete` | Delete a risk acceptance |
| `delete_risk_assessment` | `risks.assessment.delete` | Delete a risk assessment |
| `delete_risk_criteria` | `risks.criteria.delete` | Delete a risk criteria |
| `delete_risk_level` | `risks.criteria.delete` | Delete a risk level |
| `delete_risk_treatment_plan` | `risks.treatment.delete` | Delete a risk treatment plan |
| `delete_scale_level` | `risks.criteria.delete` | Delete a scale level |
| `delete_threat` | `risks.threat.delete` | Delete a threat |
| `delete_treatment_action` | `risks.treatment.delete` | Delete a treatment action |
| `delete_vulnerability` | `risks.vulnerability.delete` | Delete a vulnerability |
| `ebios_ecosystem_stakeholder_allowed_transitions` | `risks.ebios_ecosystem.read` | List the lifecycle transitions the caller may perform on a ebios ecosystem stakeholder from its current state. |
| `ebios_operational_scenario_allowed_transitions` | `risks.ebios_operational.read` | List the lifecycle transitions the caller may perform on a ebios operational scenario from its current state. |
| `ebios_risk_source_allowed_transitions` | `risks.ebios_risk_source.read` | List the lifecycle transitions the caller may perform on a ebios risk source from its current state. |
| `ebios_security_baseline_allowed_transitions` | `risks.ebios_baseline.read` | List the lifecycle transitions the caller may perform on a ebios security baseline from its current state. |
| `ebios_sr_ov_pair_allowed_transitions` | `risks.ebios_risk_source.read` | List the lifecycle transitions the caller may perform on a ebios sr ov pair from its current state. |
| `ebios_strategic_scenario_allowed_transitions` | `risks.ebios_strategic.read` | List the lifecycle transitions the caller may perform on a ebios strategic scenario from its current state. |
| `ebios_summary_allowed_transitions` | `risks.ebios_summary.read` | List the lifecycle transitions the caller may perform on a ebios summary from its current state. |
| `generate_iso27005_report` | `risks.export.read` | Generate an ISO 27005 risk assessment DOCX report for a single assessment. The report covers context, criteria, threats, vulnerabilities, analyses, consolidated risks, treatment plans and acceptances. Persisted as a Report. |
| `generate_risk_register` | `risks.export.read` | Generate an Excel (.xlsx) export of the risk register. Optional filters: scope_ids, assessment_id, status, priority. When omitted, scope filtering falls back to the user's allowed scopes. The generated file is persisted as a Report. |
| `get_ebios_attack_path_step` | `risks.ebios_strategic.read` | Get a ebios attack path step by ID |
| `get_ebios_attack_path_step_history` | `risks.ebios_strategic.read` | Return the change history of a ebios attack path step: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_attack_technique` | `risks.ebios_operational.read` | Get a ebios attack technique by ID |
| `get_ebios_attack_technique_history` | `risks.ebios_operational.read` | Return the change history of a ebios attack technique: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_baseline_gap` | `risks.ebios_baseline.read` | Get a ebios baseline gap by ID |
| `get_ebios_baseline_gap_history` | `risks.ebios_baseline.read` | Return the change history of a ebios baseline gap: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_ecosystem_stakeholder` | `risks.ebios_ecosystem.read` | Get a ebios ecosystem stakeholder by ID |
| `get_ebios_ecosystem_stakeholder_history` | `risks.ebios_ecosystem.read` | Return the change history of a ebios ecosystem stakeholder: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_feared_event` | `risks.ebios_baseline.read` | Get a ebios feared event by ID |
| `get_ebios_feared_event_history` | `risks.ebios_baseline.read` | Return the change history of a ebios feared event: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_operational_scenario` | `risks.ebios_operational.read` | Get a ebios operational scenario by ID |
| `get_ebios_operational_scenario_history` | `risks.ebios_operational.read` | Return the change history of a ebios operational scenario: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_pacs_measure` | `risks.ebios_summary.read` | Get a ebios pacs measure by ID |
| `get_ebios_pacs_measure_history` | `risks.ebios_summary.read` | Return the change history of a ebios pacs measure: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_risk_source` | `risks.ebios_risk_source.read` | Get a ebios risk source by ID |
| `get_ebios_risk_source_history` | `risks.ebios_risk_source.read` | Return the change history of a ebios risk source: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_security_baseline` | `risks.ebios_baseline.read` | Get a ebios security baseline by ID |
| `get_ebios_security_baseline_history` | `risks.ebios_baseline.read` | Return the change history of a ebios security baseline: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_sr_ov_pair` | `risks.ebios_risk_source.read` | Get a ebios sr ov pair by ID |
| `get_ebios_sr_ov_pair_history` | `risks.ebios_risk_source.read` | Return the change history of a ebios sr ov pair: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_strategic_scenario` | `risks.ebios_strategic.read` | Get a ebios strategic scenario by ID |
| `get_ebios_strategic_scenario_history` | `risks.ebios_strategic.read` | Return the change history of a ebios strategic scenario: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_study_framework` | `risks.ebios_assessment.read` | Get a ebios study framework by ID |
| `get_ebios_study_framework_history` | `risks.ebios_assessment.read` | Return the change history of a ebios study framework: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_summary` | `risks.ebios_summary.read` | Get a ebios summary by ID |
| `get_ebios_summary_history` | `risks.ebios_summary.read` | Return the change history of a ebios summary: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_targeted_objective` | `risks.ebios_risk_source.read` | Get a ebios targeted objective by ID |
| `get_ebios_targeted_objective_history` | `risks.ebios_risk_source.read` | Return the change history of a ebios targeted objective: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_ebios_workshop` | `risks.ebios_assessment.read` | Get a ebios workshop by ID |
| `get_ebios_workshop_history` | `risks.ebios_assessment.read` | Return the change history of a ebios workshop: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_iso27005_risk` | `risks.iso27005.read` | Get a iso27005 risk by ID |
| `get_iso27005_risk_history` | `risks.iso27005.read` | Return the change history of a iso27005 risk: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_mitre_attack_technique` | `risks.ebios_operational.read` | Get a MITRE ATT&CK technique by ID. |
| `get_risk` | `risks.risk.read` | Get a risk by ID |
| `get_risk_acceptance` | `risks.acceptance.read` | Get a risk acceptance by ID |
| `get_risk_acceptance_history` | `risks.acceptance.read` | Return the change history of a risk acceptance: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_risk_assessment` | `risks.assessment.read` | Get a risk assessment by ID |
| `get_risk_assessment_history` | `risks.assessment.read` | Return the change history of a risk assessment: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_risk_criteria` | `risks.criteria.read` | Get a risk criteria by ID |
| `get_risk_criteria_history` | `risks.criteria.read` | Return the change history of a risk criteria: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_risk_history` | `risks.risk.read` | Return the change history of a risk: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_risk_level` | `risks.criteria.read` | Get a risk level by ID |
| `get_risk_treatment_plan` | `risks.treatment.read` | Get a risk treatment plan by ID |
| `get_risk_treatment_plan_history` | `risks.treatment.read` | Return the change history of a risk treatment plan: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_scale_level` | `risks.criteria.read` | Get a scale level by ID |
| `get_threat` | `risks.threat.read` | Get a threat by ID |
| `get_threat_history` | `risks.threat.read` | Return the change history of a threat: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_treatment_action` | `risks.treatment.read` | Get a treatment action by ID |
| `get_vulnerability` | `risks.vulnerability.read` | Get a vulnerability by ID |
| `get_vulnerability_history` | `risks.vulnerability.read` | Return the change history of a vulnerability: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `iso27005_risk_allowed_transitions` | `risks.iso27005.read` | List the lifecycle transitions the caller may perform on a iso27005 risk from its current state. |
| `link_risk_requirements` | `risks.risk.update` | Link one or more compliance requirements to a risk. This is additive - existing links are preserved. Provide a risk_id and a list of requirement_ids to attach. |
| `link_treatment_plan_action_plans` | `risks.treatment.update` | Link one or more compliance action plans to a risk treatment plan. This is additive - existing links are preserved. Provide a treatment_plan_id and a list of action_plan_ids to attach. |
| `list_ebios_attack_path_steps` | `risks.ebios_strategic.read` | List ebios attack path steps with optional search and filters |
| `list_ebios_attack_techniques` | `risks.ebios_operational.read` | List ebios attack techniques with optional search and filters |
| `list_ebios_baseline_gaps` | `risks.ebios_baseline.read` | List ebios baseline gaps with optional search and filters |
| `list_ebios_ecosystem_stakeholders` | `risks.ebios_ecosystem.read` | List ebios ecosystem stakeholders with optional search and filters |
| `list_ebios_feared_events` | `risks.ebios_baseline.read` | List ebios feared events with optional search and filters |
| `list_ebios_operational_scenarios` | `risks.ebios_operational.read` | List ebios operational scenarios with optional search and filters |
| `list_ebios_pacs_measures` | `risks.ebios_summary.read` | List ebios pacs measures with optional search and filters |
| `list_ebios_risk_sources` | `risks.ebios_risk_source.read` | List ebios risk sources with optional search and filters |
| `list_ebios_security_baselines` | `risks.ebios_baseline.read` | List ebios security baselines with optional search and filters |
| `list_ebios_sr_ov_pairs` | `risks.ebios_risk_source.read` | List ebios sr ov pairs with optional search and filters |
| `list_ebios_strategic_scenarios` | `risks.ebios_strategic.read` | List ebios strategic scenarios with optional search and filters |
| `list_ebios_study_frameworks` | `risks.ebios_assessment.read` | List ebios study frameworks with optional search and filters |
| `list_ebios_summarys` | `risks.ebios_summary.read` | List ebios summarys with optional search and filters |
| `list_ebios_targeted_objectives` | `risks.ebios_risk_source.read` | List ebios targeted objectives with optional search and filters |
| `list_ebios_workshops` | `risks.ebios_assessment.read` | List ebios workshops with optional search and filters |
| `list_iso27005_risks` | `risks.iso27005.read` | List iso27005 risks with optional search and filters |
| `list_mitre_attack_techniques` | `risks.ebios_operational.read` | List MITRE ATT&CK techniques (Enterprise Matrix). Filterable by tactic, mitre_id and active flag. |
| `list_risk_acceptances` | `risks.acceptance.read` | List risk acceptances with optional search and filters |
| `list_risk_assessments` | `risks.assessment.read` | List risk assessments with optional search and filters |
| `list_risk_criterias` | `risks.criteria.read` | List risk criterias with optional search and filters |
| `list_risk_levels` | `risks.criteria.read` | List risk levels with optional search and filters |
| `list_risk_requirements` | `risks.risk.read` | List all compliance requirements linked to a risk. Returns requirement id, reference, number, name, compliance_status and framework_id for each linked requirement. |
| `list_risk_treatment_plans` | `risks.treatment.read` | List risk treatment plans with optional search and filters |
| `list_risks` | `risks.risk.read` | List risks with optional search and filters |
| `list_scale_levels` | `risks.criteria.read` | List scale levels with optional search and filters |
| `list_threats` | `risks.threat.read` | List threats with optional search and filters |
| `list_treatment_actions` | `risks.treatment.read` | List treatment actions with optional search and filters |
| `list_treatment_plan_action_plans` | `risks.treatment.read` | List all compliance action plans linked to a risk treatment plan. Returns action plan id, reference, name, status, priority, progress_percentage and owner_id for each link. |
| `list_vulnerabilitys` | `risks.vulnerability.read` | List vulnerabilitys with optional search and filters |
| `risk_acceptance_allowed_transitions` | `risks.acceptance.read` | List the lifecycle transitions the caller may perform on a risk acceptance from its current state. |
| `risk_allowed_transitions` | `risks.risk.read` | List the lifecycle transitions the caller may perform on a risk from its current state. |
| `risk_assessment_allowed_transitions` | `risks.assessment.read` | List the lifecycle transitions the caller may perform on a risk assessment from its current state. |
| `risk_treatment_plan_allowed_transitions` | `risks.treatment.read` | List the lifecycle transitions the caller may perform on a risk treatment plan from its current state. |
| `set_risk_requirements` | `risks.risk.update` | Replace the full set of linked requirements on a risk. All previous links are removed and replaced by the supplied list. Pass an empty requirement_ids list to clear all links. |
| `set_treatment_plan_action_plans` | `risks.treatment.update` | Replace the full set of compliance action plans linked to a risk treatment plan. All previous links are removed and replaced by the supplied list. Pass an empty action_plan_ids list to clear all links. |
| `threat_allowed_transitions` | `risks.threat.read` | List the lifecycle transitions the caller may perform on a threat from its current state. |
| `transition_ebios_ecosystem_stakeholder` | `risks.ebios_ecosystem.read` | Change the lifecycle state of a ebios ecosystem stakeholder (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_ebios_operational_scenario` | `risks.ebios_operational.read` | Change the lifecycle state of a ebios operational scenario (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_ebios_risk_source` | `risks.ebios_risk_source.read` | Change the lifecycle state of a ebios risk source (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_ebios_security_baseline` | `risks.ebios_baseline.read` | Change the lifecycle state of a ebios security baseline (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_ebios_sr_ov_pair` | `risks.ebios_risk_source.read` | Change the lifecycle state of a ebios sr ov pair (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_ebios_strategic_scenario` | `risks.ebios_strategic.read` | Change the lifecycle state of a ebios strategic scenario (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_ebios_summary` | `risks.ebios_summary.read` | Change the lifecycle state of a ebios summary (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_iso27005_risk` | `risks.iso27005.read` | Change the lifecycle state of a iso27005 risk (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_risk` | `risks.risk.read` | Change the lifecycle state of a risk (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_risk_acceptance` | `risks.acceptance.read` | Change the lifecycle state of a risk acceptance (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_risk_assessment` | `risks.assessment.read` | Change the lifecycle state of a risk assessment (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_risk_treatment_plan` | `risks.treatment.read` | Change the lifecycle state of a risk treatment plan (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_threat` | `risks.threat.read` | Change the lifecycle state of a threat (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_vulnerability` | `risks.vulnerability.read` | Change the lifecycle state of a vulnerability (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `unlink_risk_requirements` | `risks.risk.update` | Remove one or more compliance requirements from a risk. Only the specified links are removed; other links are preserved. Provide a risk_id and a list of requirement_ids to detach. |
| `unlink_treatment_plan_action_plans` | `risks.treatment.update` | Remove one or more compliance action plans from a risk treatment plan. Only the specified links are removed; other links are preserved. |
| `update_ebios_attack_path_step` | `risks.ebios_strategic.update` | Update an existing ebios attack path step |
| `update_ebios_attack_technique` | `risks.ebios_operational.update` | Update an existing ebios attack technique |
| `update_ebios_baseline_gap` | `risks.ebios_baseline.update` | Update an existing ebios baseline gap |
| `update_ebios_ecosystem_stakeholder` | `risks.ebios_ecosystem.update` | Update an existing ebios ecosystem stakeholder |
| `update_ebios_feared_event` | `risks.ebios_baseline.update` | Update an existing ebios feared event |
| `update_ebios_operational_scenario` | `risks.ebios_operational.update` | Update an existing ebios operational scenario |
| `update_ebios_pacs_measure` | `risks.ebios_summary.update` | Update an existing ebios pacs measure |
| `update_ebios_risk_source` | `risks.ebios_risk_source.update` | Update an existing ebios risk source |
| `update_ebios_security_baseline` | `risks.ebios_baseline.update` | Update an existing ebios security baseline |
| `update_ebios_sr_ov_pair` | `risks.ebios_risk_source.update` | Update an existing ebios sr ov pair |
| `update_ebios_strategic_scenario` | `risks.ebios_strategic.update` | Update an existing ebios strategic scenario |
| `update_ebios_study_framework` | `risks.ebios_assessment.update` | Update an existing ebios study framework |
| `update_ebios_summary` | `risks.ebios_summary.update` | Update an existing ebios summary |
| `update_ebios_targeted_objective` | `risks.ebios_risk_source.update` | Update an existing ebios targeted objective |
| `update_ebios_workshop` | `risks.ebios_assessment.update` | Update an existing ebios workshop |
| `update_iso27005_risk` | `risks.iso27005.update` | Update an existing iso27005 risk |
| `update_risk` | `risks.risk.update` | Update an existing risk |
| `update_risk_acceptance` | `risks.acceptance.update` | Update an existing risk acceptance |
| `update_risk_assessment` | `risks.assessment.update` | Update an existing risk assessment |
| `update_risk_criteria` | `risks.criteria.update` | Update an existing risk criteria |
| `update_risk_level` | `risks.criteria.update` | Update an existing risk level |
| `update_risk_treatment_plan` | `risks.treatment.update` | Update an existing risk treatment plan |
| `update_scale_level` | `risks.criteria.update` | Update an existing scale level |
| `update_threat` | `risks.threat.update` | Update an existing threat |
| `update_treatment_action` | `risks.treatment.update` | Update an existing treatment action |
| `update_vulnerability` | `risks.vulnerability.update` | Update an existing vulnerability |
| `vulnerability_allowed_transitions` | `risks.vulnerability.read` | List the lifecycle transitions the caller may perform on a vulnerability from its current state. |

## System and administration

| Tool | Permission | Description |
| --- | --- | --- |
| `create_user` | `system.users.create` | Provision a new user via the invitation flow so it can be referenced as an owner / reviewer. No password is accepted: the account is created with an unusable password and the response returns an 'activation_url' the invitee follows to set their first credential. 'groups' are role / group names that must already exist (use list_groups). Requires the system.users.create permission. |
| `get_company_settings` | `system.config.read` | Get the company settings (name, application name, AI assistant name, address, accent colour, whether the company logo replaces the Cairn logo) |
| `get_group` | `system.groups.read` | Get group details including permissions |
| `get_user` | `system.users.read` | Get detailed information about a user |
| `list_access_logs` | `system.audit_trail.read` | List access logs (authentication events) |
| `list_assistant_feedback` | `system.assistant_feedback.read` | List user feedback on Ask Cairn answers (thumbs up/down and optional comment), with the original question, language and the LLM response. Read-only; for quality analysis. Feedback already marked corrected is excluded unless include_resolved=true. |
| `list_groups` | `system.groups.read` | List all groups |
| `list_permissions` | `system.groups.read` | List all available permissions |
| `list_users` | `system.users.read` | List users with optional search |
| `update_company_settings` | `system.config.update` | Update company settings (name, application name, AI assistant name, address, accent colour, and/or whether the company logo replaces the Cairn logo) |

## Trust Center

| Tool | Permission | Description |
| --- | --- | --- |
| `approve_trust_center_document_request` | `trust_center.document_request.approve` | Approve a gated-document request: issues a time-limited signed download link and emails it to the requester. |
| `batch_create_trust_center_certifications` | `trust_center.certification.create` | Create or upsert multiple trust center certifications in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_trust_center_documents` | `trust_center.document.create` | Create or upsert multiple trust center documents in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_trust_center_measures` | `trust_center.measure.create` | Create or upsert multiple trust center measures in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `batch_create_trust_center_subprocessors` | `trust_center.subprocessor.create` | Create or upsert multiple trust center subprocessors in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts. |
| `create_trust_center_certification` | `trust_center.certification.create` | Create a new trust center certification |
| `create_trust_center_document` | `trust_center.document.create` | Create a new trust center document |
| `create_trust_center_measure` | `trust_center.measure.create` | Create a new trust center measure |
| `create_trust_center_subprocessor` | `trust_center.subprocessor.create` | Create a new trust center subprocessor |
| `delete_trust_center_certification` | `trust_center.certification.delete` | Delete a trust center certification |
| `delete_trust_center_document` | `trust_center.document.delete` | Delete a trust center document |
| `delete_trust_center_measure` | `trust_center.measure.delete` | Delete a trust center measure |
| `delete_trust_center_subprocessor` | `trust_center.subprocessor.delete` | Delete a trust center subprocessor |
| `get_trust_center_certification` | `trust_center.certification.read` | Get a trust center certification by ID |
| `get_trust_center_certification_history` | `trust_center.certification.read` | Return the change history of a trust center certification: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_trust_center_document` | `trust_center.document.read` | Get a trust center document by ID |
| `get_trust_center_document_history` | `trust_center.document.read` | Return the change history of a trust center document: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_trust_center_document_request` | `trust_center.document_request.read` | Get a Trust Center document request by ID. |
| `get_trust_center_measure` | `trust_center.measure.read` | Get a trust center measure by ID |
| `get_trust_center_measure_history` | `trust_center.measure.read` | Return the change history of a trust center measure: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `get_trust_center_settings` | `trust_center.settings.read` | Get the public Trust Center settings (publication switch, headline, intro, security contact, theme). |
| `get_trust_center_subprocessor` | `trust_center.subprocessor.read` | Get a trust center subprocessor by ID |
| `get_trust_center_subprocessor_history` | `trust_center.subprocessor.read` | Return the change history of a trust center subprocessor: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline. |
| `list_trust_center_certifications` | `trust_center.certification.read` | List trust center certifications with optional search and filters |
| `list_trust_center_document_requests` | `trust_center.document_request.read` | List Trust Center gated-document access requests (optionally filter by workflow_state). |
| `list_trust_center_documents` | `trust_center.document.read` | List trust center documents with optional search and filters |
| `list_trust_center_measures` | `trust_center.measure.read` | List trust center measures with optional search and filters |
| `list_trust_center_subprocessors` | `trust_center.subprocessor.read` | List trust center subprocessors with optional search and filters |
| `reject_trust_center_document_request` | `trust_center.document_request.approve` | Reject a pending gated-document request, or revoke access for an approved one. A comment is required. |
| `transition_trust_center_certification` | `trust_center.certification.read` | Change the lifecycle state of a trust center certification (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_trust_center_document` | `trust_center.document.read` | Change the lifecycle state of a trust center document (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_trust_center_measure` | `trust_center.measure.read` | Change the lifecycle state of a trust center measure (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `transition_trust_center_subprocessor` | `trust_center.subprocessor.read` | Change the lifecycle state of a trust center subprocessor (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping). |
| `trust_center_certification_allowed_transitions` | `trust_center.certification.read` | List the lifecycle transitions the caller may perform on a trust center certification from its current state. |
| `trust_center_document_allowed_transitions` | `trust_center.document.read` | List the lifecycle transitions the caller may perform on a trust center document from its current state. |
| `trust_center_measure_allowed_transitions` | `trust_center.measure.read` | List the lifecycle transitions the caller may perform on a trust center measure from its current state. |
| `trust_center_subprocessor_allowed_transitions` | `trust_center.subprocessor.read` | List the lifecycle transitions the caller may perform on a trust center subprocessor from its current state. |
| `update_trust_center_certification` | `trust_center.certification.update` | Update an existing trust center certification |
| `update_trust_center_document` | `trust_center.document.update` | Update an existing trust center document |
| `update_trust_center_measure` | `trust_center.measure.update` | Update an existing trust center measure |
| `update_trust_center_settings` | `trust_center.settings.update` | Update the public Trust Center settings. Set is_published=true to expose the public page and API; false takes the whole Trust Center offline (404). |
| `update_trust_center_subprocessor` | `trust_center.subprocessor.update` | Update an existing trust center subprocessor |
