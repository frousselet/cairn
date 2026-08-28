<!-- GENERATED FILE - DO NOT EDIT BY HAND.
     Rendered from the MCP tool registry (`mcp/tools.py`) by `python manage.py generate_docs`.
     Change the code, then re-run the command. CI fails on a stale page. -->

# MCP tool parameters : Incidents

Input schemas for the 103 `incidents` tools. The index of every module is in [mcp-tools.md](mcp-tools.md); a live server answers the same thing authoritatively through the `tools/list` JSON-RPC method.

## `batch_create_incident_evidences`

Create or upsert multiple incident evidences in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `incidents.evidence.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of incident evidence objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_incident_notifications`

Create or upsert multiple incident notifications in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `incidents.notification.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of incident notification objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_incident_response_actions`

Create or upsert multiple incident response actions in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `incidents.incident.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of incident response action objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_incident_response_plans`

Create or upsert multiple incident response plans in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `incidents.response_plan.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of incident response plan objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_incidents`

Create or upsert multiple incidents in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `incidents.incident.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of incident objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_obligation_templates`

Create or upsert multiple obligation templates in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `incidents.response_plan.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of obligation template objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_personal_data_breachs`

Create or upsert multiple personal data breachs in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `incidents.notification.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of personal data breach objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_post_incident_reviews`

Create or upsert multiple post incident reviews in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `incidents.review.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of post incident review objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_reporting_authoritys`

Create or upsert multiple reporting authoritys in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `incidents.response_plan.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of reporting authority objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `batch_create_security_events`

Create or upsert multiple security events in one call (max 500). Non-atomic: valid items are applied even if others fail. Pass 'match_on' (a list of field names, e.g. ["name"]) to make the call idempotent: each item whose match_on values already exist is UPDATED in place instead of duplicated, so a failed import can be safely replayed. Returns per-item status (created / updated / error) with created, updated and error counts.

Requires `incidents.event.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `items` | `array` | yes | Array of security event objects to create or upsert (max 500). |
| `match_on` | `array` | - | Optional business key: list of writable field names used to find an existing record (e.g. ["name"]). When an item matches, it is updated; otherwise it is created. Omit for create-only behaviour. Many-to-many fields are not allowed. |

## `create_evidence_custody_event`

Record one handling act on an evidence item. The chain of custody is append-only: there is no update and no delete tool, and a mistake is corrected by appending a further act that states what the earlier one got wrong. The actor is always the calling account and the source is always 'manual'. Do not use this to assert an integrity verdict: call verify_evidence_integrity, which measures the artefact itself.

Requires `incidents.evidence.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `evidence_id` | `string` | yes | UUID of the evidence item. Use list_incident_evidences to get valid IDs. |
| `action` | `string` | yes | The handling act being attested. transferred, released, returned and destroyed each require a named counterparty. |
| `occurred_at` | `string` | yes | Real-world time of the act (ISO 8601). This is the ledger's ordering key. |
| `counterparty` | `string` | - | Named individual on the other side of the act. A handover to an organisation with no named individual is not a handover. |
| `counterparty_organisation` | `string` | - | Organisation the counterparty belongs to. |
| `location` | `string` | - | Where the act took place. |
| `hash_at_event` | `string` | - | Digest recorded at the time of the act, when one was measured by hand. |
| `notes` | `string` | - | Free-text account of the act. |

## `create_incident`

Create a new incident

Requires `incidents.incident.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `title` | `string` | yes | Short title of the incident. |
| `summary` | `string` | - | One-paragraph executive summary, for management review and external communication. |
| `description` | `string` | - | Full narrative of the incident. |
| `category` | `string` | - | Incident category. Reuses the threat taxonomy: an incident is a threat that materialised. |
| `severity` | `string` | - | Severity, read through the response plan's classification scale. |
| `detection_source` | `string` | - | How the incident came to light. |
| `is_exercise` | `boolean` | - | Simulation or tabletop run through the real process. Exercises never generate notification obligations. |
| `tlp` | `string` | - | Traffic Light Protocol handling caveat for the incident file and its evidence. |
| `confidentiality_impact` | `boolean` | - | Confidentiality was impacted. |
| `integrity_impact` | `boolean` | - | Integrity was impacted. |
| `availability_impact` | `boolean` | - | Availability was impacted. |
| `personal_data_involved` | `boolean` | - | Personal data was, or may have been, affected. Setting it forces the GDPR Art. 33 obligation and the breach record. |
| `occurred_at` | `string` | - | Best estimate of when the incident began (ISO 8601 date-time). |
| `detected_at` | `string` | yes | Technical detection (ISO 8601 date-time). Base of the mean-time-to-detect KPI. |
| `awareness_at` | `string` | - | The legal clock anchor (GDPR Art. 33(1), NIS2 Art. 23), ISO 8601. Defaults to the detection time when left empty. |
| `awareness_justification` | `string` | - | Why legal awareness postdates technical detection. Mandatory whenever the two differ. |
| `outage_duration` | `string` | - | Measured service interruption, as a duration (e.g. '04:30:00' or '1 02:00:00'). |
| `estimated_cost` | `string` | - | Estimated cost of the incident (decimal). |
| `no_obligation_justification` | `string` | - | Why nothing is owed to anyone. Mandatory when triage produced no notification obligation. |
| `is_significant` | `boolean` | - | NIS2 Art. 23(3) significance verdict. Deliberately separate from severity. |
| `significance_determined_at` | `string` | - | When significance was determined (ISO 8601). Usable as a statutory clock anchor in its own right. |
| `significance_justification` | `string` | - | Reasoning behind the significance verdict. |
| `cross_border_impact` | `boolean` | - | Entities or users in more than one Member State are affected. |
| `cross_border_justification` | `string` | - | Reasoning behind the cross-border verdict. Mandatory once the verdict is set. |
| `suspected_malicious` | `boolean` | - | NIS2 Art. 23(4)(a): whether the incident is suspected to result from a malicious act. |
| `suspected_malicious_justification` | `string` | - | Reasoning behind the malicious-act verdict. Mandatory once the verdict is set. |
| `response_plan_id` | `string` | - | UUID of the incident response plan this incident is handled under. Use list_incident_response_plans to get valid IDs. |
| `reporter_id` | `string` | - | UUID of the user who reported it. Use list_users to get valid IDs. |
| `incident_manager_id` | `string` | - | UUID of the single accountable responder (A.5.24). Use list_users to get valid IDs. |
| `parent_incident_id` | `string` | - | UUID of the major incident this one belongs to, or the merge target. Use list_incidents to get valid IDs. |
| `origin_supplier_id` | `string` | - | UUID of the third party whose breach or outage caused this. Use list_suppliers to get valid IDs. |
| `scope_ids` | `array` | - | Scopes this incident belongs to (RG-01). Every child row inherits its tenancy from here. |
| `affected_supplier_ids` | `array` | - | Suppliers impacted or notified downstream (not the cause: that is origin_supplier_id). |
| `affected_essential_asset_ids` | `array` | - | Essential assets affected. Use list_essential_assets. |
| `affected_support_asset_ids` | `array` | - | Support assets affected. Use list_support_assets. |
| `affected_site_ids` | `array` | - | Sites affected. Use list_sites. |
| `affected_activity_ids` | `array` | - | Business activities halted. Use list_activities. |
| `threat_ids` | `array` | - | The threats that materialised. Use list_threats. |
| `exploited_vulnerability_ids` | `array` | - | Vulnerabilities exploited. Use list_vulnerabilities. |
| `realised_risk_ids` | `array` | - | Registered risks that actually materialised. Use list_risks. |
| `linked_requirement_ids` | `array` | - | Controls in play. Use list_requirements. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_incident_evidence`

Create a new incident evidence

Requires `incidents.evidence.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `incident_id` | `string` | yes | UUID of the parent incident. Use list_incidents to get valid IDs. |
| `title` | `string` | yes | Name of the artefact. |
| `description` | `string` | - | What the artefact is and why it matters. |
| `evidence_type` | `string` | yes | Kind of artefact. |
| `tlp` | `string` | - | Traffic Light Protocol handling caveat. Defaults to red. |
| `collected_at` | `string` | - | Acquisition date-time (ISO 8601). Frozen once the item is sealed. |
| `collected_by_id` | `string` | - | UUID of the user who acquired it. Frozen once sealed. Use list_users. |
| `collection_method` | `string` | - | How it was acquired. Frozen once sealed. |
| `source_support_asset_id` | `string` | - | UUID of the support asset the artefact came from. Use list_support_assets. |
| `source_description` | `string` | - | Free-text description of the source when no asset is recorded. |
| `content_hash` | `string` | - | Hex digest of the artefact. Frozen once sealed. Never assert a verification verdict by writing here: call verify_evidence_integrity. |
| `hash_algorithm` | `string` | - | Digest algorithm the content hash was measured with. Frozen once sealed. |
| `original_filename` | `string` | - | Filename the artefact was acquired under. |
| `file_size` | `integer` | - | Size of the artefact in bytes. |
| `storage_location` | `string` | - | Where the artefact actually is, for an item registered by reference. |
| `legal_hold` | `boolean` | - | Under legal hold: destruction is refused while set. |
| `retention_until` | `string` | - | Retention expiry date (ISO 8601 date). |
| `admissibility_notes` | `string` | - | Notes bearing on the artefact's admissibility. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_incident_notification`

Create a new incident notification

Requires `incidents.notification.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `incident_id` | `string` | yes | UUID of the parent incident. Use list_incidents to get valid IDs. |
| `regime` | `string` | yes | The regulatory regime this obligation arises under. |
| `recipient_kind` | `string` | yes | Who the notification is owed to. |
| `authority_id` | `string` | - | UUID of the body the filing goes to. Use list_reporting_authoritys. |
| `recipient_stakeholder_id` | `string` | - | UUID of the stakeholder recipient. Use list_stakeholders. |
| `recipient_supplier_id` | `string` | - | UUID of the supplier recipient. Use list_suppliers. |
| `recipient_name` | `string` | - | Free-text recipient, when it is none of the three modelled kinds. |
| `obligation_reference` | `string` | - | The article the duty comes from, snapshotted from the template. |
| `content_requirements` | `string` | - | What the law requires this filing to contain, snapshotted from the template. |
| `clock_anchor` | `string` | - | Which incident timestamp the statutory clock runs from. Frozen once the obligation has been filed. |
| `deadline_hours` | `integer` | - | Hours from the anchor to the deadline. Frozen once filed. |
| `no_fixed_deadline` | `boolean` | - | The regime imposes no fixed deadline. |
| `depends_on_id` | `string` | - | UUID of the obligation whose first filing anchors this one's clock. Use list_incident_notifications. |
| `channel` | `string` | - | How the notification is transmitted. |
| `content` | `string` | - | The text that is filed. Frozen once the obligation has been sent: an amendment is a further filing. |
| `decision_rationale` | `string` | - | Why the obligation is required, or why it is not. The decision itself is a transition, not a field write. |
| `acknowledgement_reference` | `string` | - | Reference the recipient returned on acknowledgement. |
| `acknowledged_at` | `string` | - | When the recipient acknowledged (ISO 8601). |
| `proof_evidence_id` | `string` | - | UUID of the evidence item holding the proof of filing. Use list_incident_evidences. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_incident_response_action`

Create a new incident response action

Requires `incidents.incident.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `incident_id` | `string` | yes | UUID of the parent incident. Use list_incidents to get valid IDs. |
| `action_type` | `string` | yes | Which ISO 27035 response step this action belongs to. |
| `title` | `string` | yes | What is being done, in the imperative. |
| `description` | `string` | - | The command to run, the runbook section, the person to call. |
| `status` | `string` | - | Operational progress. A plain status column, not a lifecycle state. |
| `owner_id` | `string` | - | UUID of the user accountable for the step. Use list_users. |
| `performed_by_id` | `string` | - | UUID of the user who actually executed it. Use list_users. |
| `due_at` | `string` | - | Due date-time (ISO 8601). Drives the escalation sweep. |
| `started_at` | `string` | - | Execution start (ISO 8601). |
| `completed_at` | `string` | - | Execution end (ISO 8601). |
| `outcome` | `string` | - | What the action actually achieved. A containment step marked done with no stated outcome is not evidence of containment. |
| `effectiveness` | `string` | - | Whether the step worked, assessed during the post-incident review (A.5.27). |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_incident_response_plan`

Create a new incident response plan

Requires `incidents.response_plan.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | Name of the response plan. |
| `purpose` | `string` | - | What the plan is for. |
| `procedure` | `string` | - | Response procedure (HTML rich text) |
| `classification_scale` | `string` | - | What low / medium / high / critical mean in this organisation's terms (HTML rich text) |
| `escalation_matrix` | `string` | - | Who is escalated to, at which severity, within which delay (HTML rich text) |
| `reporting_channels` | `string` | - | How events and weaknesses are reported, including the anonymous channel A.6.8 requires (HTML rich text) |
| `evidence_procedure` | `string` | - | Identification, collection, acquisition and preservation of evidence (A.5.28) (HTML rich text) |
| `lessons_learned_procedure` | `string` | - | How knowledge gained from incidents strengthens controls (A.5.27) (HTML rich text) |
| `applicable_regimes` | `array` | - | Regulatory regimes this plan is built to satisfy. Triage instantiates one notification obligation per applicable regime. |
| `owner_id` | `string` | - | UUID of the plan owner. Use list_users to get valid IDs. |
| `approved_by_id` | `string` | - | UUID of the approver. Use list_users to get valid IDs. |
| `approved_at` | `string` | - | Approval date (ISO 8601 date). |
| `effective_from` | `string` | - | Date the plan takes effect (ISO 8601 date). |
| `review_date` | `string` | - | Next review date (ISO 8601 date). |
| `scope_ids` | `array` | - | Scopes this plan covers (RG-01). |
| `responsible_role_ids` | `array` | - | Roles accountable under this plan. Use list_roles. |
| `linked_requirement_ids` | `array` | - | Requirements this plan satisfies. Use list_requirements. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_incident_timeline_entry`

Append one entry to an incident's chronology. The chronology is append-only: there is no update and no delete tool. A mistake is corrected by appending a further entry of type 'correction' that names the entry it supersedes and states why. The author is always the calling account and the source is always 'manual'.

Requires `incidents.incident.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `incident_id` | `string` | yes | UUID of the incident. Use list_incidents to get valid IDs. |
| `occurred_at` | `string` | yes | Real-world time of the act being narrated (ISO 8601). May be backdated: the chronology reads in the order things happened. |
| `summary` | `string` | yes | The one-line entry, exported verbatim (max 500 characters). |
| `detail` | `string` | - | The full account: commands run, output observed, people spoken to. |
| `entry_type` | `string` | - | Kind of entry. |
| `is_evidence` | `boolean` | - | Include this entry verbatim in generated regulatory filings and in the incident file. |
| `related_action_id` | `string` | - | UUID of the response action this entry narrates. Use list_incident_response_actions. |
| `related_evidence_id` | `string` | - | UUID of the evidence item this entry narrates. Use list_incident_evidences. |
| `superseded_entry_id` | `string` | - | UUID of the earlier entry this one corrects. Requires entry_type 'correction' and a correction_reason. |
| `correction_reason` | `string` | - | Why the earlier entry was wrong. A correction with no stated reason is a rewrite. |

## `create_notification_filing`

Record that a notification obligation was actually transmitted. The filing log is append-only: there is no update and no delete tool, and an amendment is a further filing, never a rewrite. The first filing on an obligation runs through the lifecycle and freezes its lateness verdict; later filings insert without disturbing it. The submitter is always the calling account.

Requires `incidents.notification.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `notification_id` | `string` | yes | UUID of the obligation being discharged. Use list_incident_notifications to get valid IDs. |
| `submitted_at` | `string` | - | When the transmission was made (ISO 8601). Defaults to now. Cannot be in the future. |
| `channel` | `string` | - | How it was transmitted. Defaults to the obligation's channel, then to 'portal'. |
| `recipient_name` | `string` | - | Who it was transmitted to. Defaults to the obligation's recipient. |
| `subject` | `string` | - | Subject line of the transmission. |
| `content` | `string` | - | What was actually transmitted, verbatim. |
| `external_reference` | `string` | - | Reference the portal or recipient returned. |
| `is_correction` | `boolean` | - | This filing corrects an earlier one. The first filing on an obligation is never a correction. |
| `supersedes_id` | `string` | - | UUID of the filing this one replaces, on the same obligation. Implies is_correction. |
| `comment` | `string` | - | Comment carried into the lifecycle transition performed by a first filing. |

## `create_obligation_template`

Create a new obligation template

Requires `incidents.response_plan.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | Name of the catalogue rule. |
| `authority_id` | `string` | - | UUID of the body the filing goes to. Use list_reporting_authoritys to get valid IDs. |
| `regime` | `string` | yes | The regulatory regime this rule instantiates. |
| `recipient_kind` | `string` | yes | Who the notification is owed to. |
| `legal_reference` | `string` | - | The article the duty comes from (e.g. 'GDPR Art. 33(1)'). |
| `content_requirements` | `string` | - | What the law requires the filing to contain. |
| `clock_anchor` | `string` | - | Which incident timestamp the statutory clock runs from. |
| `clock_hours` | `integer` | - | Hours from the anchor to the deadline (e.g. 72 for GDPR Art. 33). |
| `no_fixed_deadline` | `boolean` | - | The regime imposes no fixed deadline. Distinct from a clock that has simply not started. |
| `depends_on_regime` | `string` | - | The sibling regime whose first filing anchors this staged obligation. |
| `jurisdiction_country` | `string` | - | Country this rule applies in. |
| `min_severity` | `string` | - | Severity floor below which the obligation is not raised. |
| `requires_significant` | `boolean` | - | Only raised when the incident is NIS2-significant. |
| `requires_personal_data` | `boolean` | - | Only raised when personal data is involved. |
| `requires_high_risk` | `boolean` | - | Only raised when the breach is high risk to rights and freedoms. |
| `requires_cross_border` | `boolean` | - | Only raised when the incident is cross-border. |
| `controller_roles` | `array` | - | GDPR controller roles this rule applies to. |
| `applicable_categories` | `array` | - | Incident categories this rule applies to. Empty means all. |
| `order` | `integer` | - | Display / generation order within the catalogue. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_personal_data_breach`

Create a new personal data breach

Requires `incidents.notification.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `incident_id` | `string` | yes | UUID of the incident this breach record qualifies (one per incident). Use list_incidents. |
| `controller_role` | `string` | - | The organisation's GDPR role for this processing. |
| `controller_supplier_id` | `string` | - | UUID of the controller we act as processor for. Use list_suppliers. |
| `lead_authority_id` | `string` | - | UUID of the lead supervisory authority. Use list_reporting_authoritys. |
| `cross_border_eu` | `boolean` | - | Data subjects in more than one Member State are affected. |
| `nature` | `string` | - | Nature of the breach (GDPR Art. 33(3)(a)). |
| `data_categories` | `array` | - | Categories of personal data affected (free-form list). |
| `data_subject_categories` | `array` | - | Categories of data subject affected (free-form list). |
| `approximate_data_subjects` | `integer` | - | Approximate number of data subjects concerned. |
| `approximate_records` | `integer` | - | Approximate number of personal data records concerned. |
| `special_categories` | `boolean` | - | Art. 9 special-category data is involved. |
| `volume_is_estimate` | `boolean` | - | The two counts are estimates rather than measured figures. |
| `dpo_contact` | `string` | - | Contact point for the DPO (GDPR Art. 33(3)(b)). |
| `likely_consequences` | `string` | - | Likely consequences of the breach (GDPR Art. 33(3)(c)). |
| `measures_taken` | `string` | - | Measures taken or proposed (GDPR Art. 33(3)(d)). |
| `high_risk_to_rights` | `boolean` | - | High risk to the rights and freedoms of natural persons (GDPR Art. 34(1)). |
| `high_risk_justification` | `string` | - | Reasoning behind the high-risk verdict. |
| `article_34_exemption` | `string` | - | Ground relied on to omit the communication to data subjects (GDPR Art. 34(3)). |
| `article_34_exemption_justification` | `string` | - | Reasoning behind the Art. 34(3) exemption. |
| `register_entry_reference` | `string` | - | Reference of the matching entry in the Art. 33(5) internal breach register. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_post_incident_review`

Create a new post incident review

Requires `incidents.review.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `incident_id` | `string` | yes | UUID of the incident being reviewed (one review per incident). Use list_incidents. |
| `response_plan_id` | `string` | - | UUID of the response plan the incident was handled under. Use list_incident_response_plans. |
| `scheduled_date` | `string` | - | Date the review is scheduled for (ISO 8601 date). |
| `facilitator_id` | `string` | - | UUID of the user facilitating the review. Use list_users. |
| `root_cause_method` | `string` | - | Root cause analysis method used. |
| `root_cause` | `string` | - | The root cause as determined by the analysis. |
| `contributing_factors` | `string` | - | Factors that contributed without being the root cause. |
| `detection_gap` | `string` | - | Why detection took as long as it did. |
| `containment_assessment` | `string` | - | How well containment worked. |
| `what_went_well` | `string` | - | What the response got right. |
| `what_failed` | `string` | - | What the response got wrong. |
| `recurrence_likelihood` | `string` | - | Likelihood the incident recurs. |
| `similar_incidents_checked` | `boolean` | - | Whether the register was checked for similar incidents (A.5.27). |
| `risk_reassessment_required` | `boolean` | - | A risk reassessment is owed. |
| `response_plan_update_required` | `boolean` | - | The response plan needs updating. |
| `training_required` | `boolean` | - | Training or awareness action is owed. |
| `effectiveness_review_date` | `string` | - | Date the effectiveness of the corrective actions is to be re-checked (ISO 8601 date). |
| `effectiveness_verdict` | `string` | - | ISO 27001 clause 10.2 d): did the corrective action actually work. |
| `effectiveness_reviewed_by_id` | `string` | - | UUID of the user who assessed effectiveness. Use list_users. |
| `effectiveness_notes` | `string` | - | Reasoning behind the effectiveness verdict. |
| `participant_ids` | `array` | - | Users who took part in the review. Use list_users. |
| `raised_finding_ids` | `array` | - | Findings raised by the review. Use list_findings. |
| `corrective_action_plan_ids` | `array` | - | Corrective action plans opened. Use list_action_plans. |
| `failed_control_ids` | `array` | - | Requirements whose control failed. Use list_requirements. |
| `control_to_strengthen_ids` | `array` | - | Requirements whose control must be strengthened. Use list_requirements. |
| `identified_risk_ids` | `array` | - | Risks identified by the review. Use list_risks. |
| `identified_vulnerability_ids` | `array` | - | Vulnerabilities identified by the review. Use list_vulnerabilities. |
| `isms_change_ids` | `array` | - | ISMS changes triggered by the review. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_reporting_authority`

Create a new reporting authority

Requires `incidents.response_plan.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `name` | `string` | yes | Full name of the body. |
| `short_name` | `string` | - | Common abbreviation (e.g. CNIL, ANSSI). |
| `authority_type` | `string` | - | Kind of body. |
| `primary_regime` | `string` | yes | The regime this body is primarily the recipient for. |
| `additional_regimes` | `array` | - | Further regimes this body also receives filings under. |
| `jurisdiction_country` | `string` | - | Country whose jurisdiction the body exercises. |
| `portal_url` | `string` | - | URL of the online filing portal. |
| `contact_email` | `string` | - | Contact email address. |
| `contact_phone` | `string` | - | Contact phone number. |
| `notification_language` | `string` | - | Language filings must be written in (e.g. fr, en). |
| `procedure` | `string` | - | How a filing is actually made with this body. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `create_security_event`

Create a new security event

Requires `incidents.event.create`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `title` | `string` | yes | Short title of the observation. |
| `description` | `string` | - | What was observed, in the reporter's own words. Never rewritten on promotion. |
| `event_class` | `string` | - | What kind of occurrence this is. Governs which promotion targets are legal. |
| `category` | `string` | - | Provisional classification, refined on promotion. |
| `detection_source` | `string` | - | How the event came to light. |
| `source_reference` | `string` | - | SIEM alert id, ticket number or CERT bulletin reference. |
| `occurred_at` | `string` | - | Best estimate of when the occurrence started (ISO 8601). |
| `detected_at` | `string` | yes | When it was detected (ISO 8601). Base of the mean-time-to-detect KPI. |
| `reported_at` | `string` | yes | When it reached the incident response function (ISO 8601). |
| `is_anonymous` | `boolean` | - | Reported through the anonymous channel A.6.8 requires. |
| `reporter_id` | `string` | - | UUID of the reporting user. Use list_users to get valid IDs. |
| `reporter_label` | `string` | - | Identity of an external or non-user reporter: a customer, a researcher, an anonymous line. |
| `reported_by_supplier_id` | `string` | - | UUID of the supplier that notified us (NIS2 supply chain, GDPR Art. 33(2)). Use list_suppliers. |
| `duplicate_of_id` | `string` | - | UUID of the earlier security event this one repeats. Use list_security_events. |
| `assessed_by_id` | `string` | - | UUID of the user who performed the A.5.25 assessment. Use list_users. |
| `assessment_notes` | `string` | - | The reasoning behind the triage decision. An undocumented assessment is not an assessment. |
| `scope_ids` | `array` | - | Scopes this event belongs to (RG-01). A promoted incident inherits them. |
| `affected_support_asset_ids` | `array` | - | Support assets involved. Use list_support_assets. |
| `affected_essential_asset_ids` | `array` | - | Essential assets involved. Use list_essential_assets. |
| `affected_site_ids` | `array` | - | Sites involved. Use list_sites. |
| `created_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |
| `updated_at` | `string` | - | Optional ISO 8601 date-time to preserve from a legacy system on bulk import (e.g. 2023-05-12T09:00:00Z). Requires the 'system.data_import.override_dates' permission; ignored without it. |

## `declare_incident_from_event`

Promote an assessed security event into an incident, as one atomic act. Creates the incident in draft, carries over the event's title, description, detection source, timestamps, reporter, scopes and affected assets, declares it through its lifecycle, links the event to it and moves the event to its confirmed-incident step. Requires both incidents.event.validate (via the transition) and incidents.incident.create. The event must be under assessment. Optional arguments override the values carried across.

Requires `incidents.event.validate`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the security event to promote. Use list_security_events to get valid IDs. |
| `comment` | `string` | yes | Why the assessment concluded this is an incident. Mandatory: the transition records it. |
| `title` | `string` | - | Override the incident title (defaults to the event's). |
| `summary` | `string` | - | Executive summary for the new incident. |
| `description` | `string` | - | Override the incident description (defaults to the event's). |
| `category` | `string` | - | Override the incident category. |
| `severity` | `string` | - | Severity of the new incident. |
| `tlp` | `string` | - | Handling caveat for the new incident. |
| `is_exercise` | `boolean` | - | The new incident is an exercise. Exercises raise no notification obligation. |
| `personal_data_involved` | `boolean` | - | Personal data was, or may have been, affected. |
| `awareness_at` | `string` | - | Legal awareness anchor for the new incident (ISO 8601). |
| `awareness_justification` | `string` | - | Why legal awareness postdates technical detection. Mandatory whenever the two differ. |
| `incident_manager_id` | `string` | - | UUID of the accountable responder. Use list_users. |
| `response_plan_id` | `string` | - | UUID of the response plan to handle it under. Use list_incident_response_plans. |

## `delete_incident`

Delete a incident

Requires `incidents.incident.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_incident_evidence`

Delete a incident evidence

Requires `incidents.evidence.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_incident_notification`

Delete a incident notification

Requires `incidents.notification.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_incident_response_action`

Delete a incident response action

Requires `incidents.incident.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_incident_response_plan`

Delete a incident response plan

Requires `incidents.response_plan.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_obligation_template`

Delete a obligation template

Requires `incidents.response_plan.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_personal_data_breach`

Delete a personal data breach

Requires `incidents.notification.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_post_incident_review`

Delete a post incident review

Requires `incidents.review.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_reporting_authority`

Delete a reporting authority

Requires `incidents.response_plan.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `delete_security_event`

Delete a security event

Requires `incidents.event.delete`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_evidence_custody_event`

Get a evidence custody event by ID

Requires `incidents.evidence.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_evidence_custody_event_history`

Return the change history of a evidence custody event. On an append-only ledger this is the tamper-detection surface: a row whose trail shows more writes than the design allows has been altered outside the supported paths.

Requires `incidents.evidence.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the evidence custody event |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_incident`

Get a incident by ID

Requires `incidents.incident.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_incident_evidence`

Get a incident evidence by ID

Requires `incidents.evidence.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_incident_evidence_history`

Return the change history of a incident evidence: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `incidents.evidence.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the incident evidence |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_incident_history`

Return the change history of a incident: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `incidents.incident.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the incident |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_incident_notification`

Get a incident notification by ID

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_incident_notification_history`

Return the change history of a incident notification: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the incident notification |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_incident_response_action`

Get a incident response action by ID

Requires `incidents.incident.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_incident_response_action_history`

Return the change history of a incident response action: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `incidents.incident.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the incident response action |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_incident_response_plan`

Get a incident response plan by ID

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_incident_response_plan_history`

Return the change history of a incident response plan: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the incident response plan |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_incident_timeline_entry`

Get a incident timeline entry by ID

Requires `incidents.incident.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_incident_timeline_entry_history`

Return the change history of a incident timeline entry. On an append-only ledger this is the tamper-detection surface: a row whose trail shows more writes than the design allows has been altered outside the supported paths.

Requires `incidents.incident.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the incident timeline entry |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_notification_filing`

Get a notification filing by ID

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_notification_filing_history`

Return the change history of a notification filing. On an append-only ledger this is the tamper-detection surface: a row whose trail shows more writes than the design allows has been altered outside the supported paths.

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the notification filing |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_obligation_template`

Get a obligation template by ID

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_obligation_template_history`

Return the change history of a obligation template: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the obligation template |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_personal_data_breach`

Get a personal data breach by ID

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_personal_data_breach_history`

Return the change history of a personal data breach: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the personal data breach |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_post_incident_review`

Get a post incident review by ID

Requires `incidents.review.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_post_incident_review_history`

Return the change history of a post incident review: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `incidents.review.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the post incident review |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_reporting_authority`

Get a reporting authority by ID

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_reporting_authority_history`

Return the change history of a reporting authority: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the reporting authority |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `get_security_event`

Get a security event by ID

Requires `incidents.event.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `get_security_event_history`

Return the change history of a security event: field-level diffs, approval events and lifecycle transitions (with comments where recorded) merged into one reverse-chronological timeline.

Requires `incidents.event.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the security event |
| `limit` | `integer` | - | Max entries (default 100, max 500). |
| `offset` | `integer` | - | Entries to skip (pagination). |

## `incident_allowed_transitions`

List the lifecycle transitions the caller may perform on a incident from its current state.

Requires `incidents.incident.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `incident_evidence_allowed_transitions`

List the lifecycle transitions the caller may perform on a incident evidence from its current state.

Requires `incidents.evidence.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `incident_notification_allowed_transitions`

List the lifecycle transitions the caller may perform on a incident notification from its current state.

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `incident_response_plan_allowed_transitions`

List the lifecycle transitions the caller may perform on a incident response plan from its current state.

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `list_evidence_custody_events`

List evidence custody events with optional search and filters. Append-only ledger: there is no update or delete tool for it.

Requires `incidents.evidence.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `evidence_id` | `string` | - | Filter by evidence_id |
| `action` | `string` | - | Filter by action |
| `source` | `string` | - | Filter by source |
| `integrity_ok` | `string` | - | Filter by integrity_ok |
| `actor_id` | `string` | - | Filter by actor_id |

## `list_incident_evidences`

List incident evidences with optional search and filters

Requires `incidents.evidence.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `incident_id` | `string` | - | Filter by incident_id |
| `evidence_type` | `string` | - | Filter by evidence_type |
| `hash_algorithm` | `string` | - | Filter by hash_algorithm |
| `tlp` | `string` | - | Filter by tlp |
| `legal_hold` | `string` | - | Filter by legal_hold |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `collected_by_id` | `string` | - | Filter by collected_by_id |

## `list_incident_notifications`

List incident notifications with optional search and filters

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `incident_id` | `string` | - | Filter by incident_id |
| `regime` | `string` | - | Filter by regime |
| `recipient_kind` | `string` | - | Filter by recipient_kind |
| `decision` | `string` | - | Filter by decision |
| `channel` | `string` | - | Filter by channel |
| `source` | `string` | - | Filter by source |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `authority_id` | `string` | - | Filter by authority_id |
| `template_id` | `string` | - | Filter by template_id |
| `no_fixed_deadline` | `string` | - | Filter by no_fixed_deadline |

## `list_incident_response_actions`

List incident response actions with optional search and filters

Requires `incidents.incident.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `incident_id` | `string` | - | Filter by incident_id |
| `action_type` | `string` | - | Filter by action_type |
| `status` | `string` | - | Filter by status |
| `owner_id` | `string` | - | Filter by owner_id |
| `performed_by_id` | `string` | - | Filter by performed_by_id |
| `effectiveness` | `string` | - | Filter by effectiveness |

## `list_incident_response_plans`

List incident response plans with optional search and filters

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `owner_id` | `string` | - | Filter by owner_id |
| `approved_by_id` | `string` | - | Filter by approved_by_id |

## `list_incident_timeline_entries`

List incident timeline entrys with optional search and filters. Append-only ledger: there is no update or delete tool for it.

Requires `incidents.incident.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `incident_id` | `string` | - | Filter by incident_id |
| `entry_type` | `string` | - | Filter by entry_type |
| `source` | `string` | - | Filter by source |
| `is_evidence` | `string` | - | Filter by is_evidence |
| `author_id` | `string` | - | Filter by author_id |

## `list_incidents`

List incidents with optional search and filters

Requires `incidents.incident.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `category` | `string` | - | Filter by category |
| `severity` | `string` | - | Filter by severity |
| `detection_source` | `string` | - | Filter by detection_source |
| `tlp` | `string` | - | Filter by tlp |
| `is_exercise` | `string` | - | Filter by is_exercise |
| `personal_data_involved` | `string` | - | Filter by personal_data_involved |
| `is_significant` | `string` | - | Filter by is_significant |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `incident_manager_id` | `string` | - | Filter by incident_manager_id |
| `response_plan_id` | `string` | - | Filter by response_plan_id |
| `parent_incident_id` | `string` | - | Filter by parent_incident_id |

## `list_notification_filings`

List notification filings with optional search and filters. Append-only ledger: there is no update or delete tool for it.

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `notification_id` | `string` | - | Filter by notification_id |
| `channel` | `string` | - | Filter by channel |
| `outcome` | `string` | - | Filter by outcome |
| `is_correction` | `string` | - | Filter by is_correction |
| `was_late` | `string` | - | Filter by was_late |
| `submitted_by_id` | `string` | - | Filter by submitted_by_id |

## `list_obligation_templates`

List obligation templates with optional search and filters

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `regime` | `string` | - | Filter by regime |
| `recipient_kind` | `string` | - | Filter by recipient_kind |
| `authority_id` | `string` | - | Filter by authority_id |
| `jurisdiction_country` | `string` | - | Filter by jurisdiction_country |
| `min_severity` | `string` | - | Filter by min_severity |
| `no_fixed_deadline` | `string` | - | Filter by no_fixed_deadline |
| `workflow_state` | `string` | - | Filter by workflow_state |

## `list_overdue_incident_notifications`

List every notification obligation whose statutory deadline has passed with no filing recorded: the 'are we late' question answered in one call. Returns the obligation, its regime and recipient, the deadline, how many hours it is overdue, and the incident it belongs to with its manager. Obligations with no deadline, already filed, or in a terminal step are excluded.

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `incident_id` | `string` | - | Restrict to one incident. |
| `regime` | `string` | - | Restrict to one regulatory regime. |
| `recipient_kind` | `string` | - | Restrict to one kind of recipient. |
| `authority_id` | `string` | - | Restrict to one reporting authority. |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |

## `list_personal_data_breachs`

List personal data breachs with optional search and filters

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `incident_id` | `string` | - | Filter by incident_id |
| `controller_role` | `string` | - | Filter by controller_role |
| `article_34_exemption` | `string` | - | Filter by article_34_exemption |
| `high_risk_to_rights` | `string` | - | Filter by high_risk_to_rights |
| `special_categories` | `string` | - | Filter by special_categories |
| `cross_border_eu` | `string` | - | Filter by cross_border_eu |
| `workflow_state` | `string` | - | Filter by workflow_state |

## `list_post_incident_reviews`

List post incident reviews with optional search and filters

Requires `incidents.review.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `incident_id` | `string` | - | Filter by incident_id |
| `root_cause_method` | `string` | - | Filter by root_cause_method |
| `recurrence_likelihood` | `string` | - | Filter by recurrence_likelihood |
| `effectiveness_verdict` | `string` | - | Filter by effectiveness_verdict |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `facilitator_id` | `string` | - | Filter by facilitator_id |

## `list_reporting_authoritys`

List reporting authoritys with optional search and filters

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `authority_type` | `string` | - | Filter by authority_type |
| `primary_regime` | `string` | - | Filter by primary_regime |
| `jurisdiction_country` | `string` | - | Filter by jurisdiction_country |
| `workflow_state` | `string` | - | Filter by workflow_state |

## `list_security_events`

List security events with optional search and filters

Requires `incidents.event.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `search` | `string` | - | Text search query |
| `limit` | `integer` | - | Max items to return (default 25, max 100) |
| `offset` | `integer` | - | Offset for pagination |
| `event_class` | `string` | - | Filter by event_class |
| `category` | `string` | - | Filter by category |
| `detection_source` | `string` | - | Filter by detection_source |
| `is_anonymous` | `string` | - | Filter by is_anonymous |
| `triage_decision` | `string` | - | Filter by triage_decision |
| `workflow_state` | `string` | - | Filter by workflow_state |
| `incident_id` | `string` | - | Filter by incident_id |
| `reported_by_supplier_id` | `string` | - | Filter by reported_by_supplier_id |

## `obligation_template_allowed_transitions`

List the lifecycle transitions the caller may perform on a obligation template from its current state.

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `personal_data_breach_allowed_transitions`

List the lifecycle transitions the caller may perform on a personal data breach from its current state.

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `post_incident_review_allowed_transitions`

List the lifecycle transitions the caller may perform on a post incident review from its current state.

Requires `incidents.review.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `reporting_authority_allowed_transitions`

List the lifecycle transitions the caller may perform on a reporting authority from its current state.

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `security_event_allowed_transitions`

List the lifecycle transitions the caller may perform on a security event from its current state.

Requires `incidents.event.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object |

## `transition_incident`

Change the lifecycle state of a incident (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `incidents.incident.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the incident |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_incident_evidence`

Change the lifecycle state of a incident evidence (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `incidents.evidence.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the incident evidence |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_incident_notification`

Change the lifecycle state of a incident notification (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the incident notification |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_incident_response_plan`

Change the lifecycle state of a incident response plan (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the incident response plan |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_obligation_template`

Change the lifecycle state of a obligation template (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the obligation template |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_personal_data_breach`

Change the lifecycle state of a personal data breach (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `incidents.notification.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the personal data breach |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_post_incident_review`

Change the lifecycle state of a post incident review (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `incidents.review.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the post incident review |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_reporting_authority`

Change the lifecycle state of a reporting authority (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `incidents.response_plan.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the reporting authority |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `transition_security_event`

Change the lifecycle state of a security event (e.g. draft -> pending -> validated -> archived). The transition is validated against the entity's workflow: required permission, mandatory comment, and side effects (owner notification on submit, validation stamping).

Requires `incidents.event.read`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the security event |
| `target_state` | `string` | yes | Target lifecycle state code (see <entity>_allowed_transitions). |
| `comment` | `string` | - | Comment, mandatory for transitions that require one. |

## `update_incident`

Update an existing incident

Requires `incidents.incident.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `title` | `string` | - | Short title of the incident. |
| `summary` | `string` | - | One-paragraph executive summary, for management review and external communication. |
| `description` | `string` | - | Full narrative of the incident. |
| `category` | `string` | - | Incident category. Reuses the threat taxonomy: an incident is a threat that materialised. |
| `severity` | `string` | - | Severity, read through the response plan's classification scale. |
| `detection_source` | `string` | - | How the incident came to light. |
| `is_exercise` | `boolean` | - | Simulation or tabletop run through the real process. Exercises never generate notification obligations. |
| `tlp` | `string` | - | Traffic Light Protocol handling caveat for the incident file and its evidence. |
| `confidentiality_impact` | `boolean` | - | Confidentiality was impacted. |
| `integrity_impact` | `boolean` | - | Integrity was impacted. |
| `availability_impact` | `boolean` | - | Availability was impacted. |
| `personal_data_involved` | `boolean` | - | Personal data was, or may have been, affected. Setting it forces the GDPR Art. 33 obligation and the breach record. |
| `occurred_at` | `string` | - | Best estimate of when the incident began (ISO 8601 date-time). |
| `detected_at` | `string` | - | Technical detection (ISO 8601 date-time). Base of the mean-time-to-detect KPI. |
| `awareness_at` | `string` | - | The legal clock anchor (GDPR Art. 33(1), NIS2 Art. 23), ISO 8601. Defaults to the detection time when left empty. |
| `awareness_justification` | `string` | - | Why legal awareness postdates technical detection. Mandatory whenever the two differ. |
| `outage_duration` | `string` | - | Measured service interruption, as a duration (e.g. '04:30:00' or '1 02:00:00'). |
| `estimated_cost` | `string` | - | Estimated cost of the incident (decimal). |
| `no_obligation_justification` | `string` | - | Why nothing is owed to anyone. Mandatory when triage produced no notification obligation. |
| `is_significant` | `boolean` | - | NIS2 Art. 23(3) significance verdict. Deliberately separate from severity. |
| `significance_determined_at` | `string` | - | When significance was determined (ISO 8601). Usable as a statutory clock anchor in its own right. |
| `significance_justification` | `string` | - | Reasoning behind the significance verdict. |
| `cross_border_impact` | `boolean` | - | Entities or users in more than one Member State are affected. |
| `cross_border_justification` | `string` | - | Reasoning behind the cross-border verdict. Mandatory once the verdict is set. |
| `suspected_malicious` | `boolean` | - | NIS2 Art. 23(4)(a): whether the incident is suspected to result from a malicious act. |
| `suspected_malicious_justification` | `string` | - | Reasoning behind the malicious-act verdict. Mandatory once the verdict is set. |
| `response_plan_id` | `string` | - | UUID of the incident response plan this incident is handled under. Use list_incident_response_plans to get valid IDs. |
| `reporter_id` | `string` | - | UUID of the user who reported it. Use list_users to get valid IDs. |
| `incident_manager_id` | `string` | - | UUID of the single accountable responder (A.5.24). Use list_users to get valid IDs. |
| `parent_incident_id` | `string` | - | UUID of the major incident this one belongs to, or the merge target. Use list_incidents to get valid IDs. |
| `origin_supplier_id` | `string` | - | UUID of the third party whose breach or outage caused this. Use list_suppliers to get valid IDs. |
| `scope_ids` | `array` | - | Scopes this incident belongs to (RG-01). Every child row inherits its tenancy from here. |
| `affected_supplier_ids` | `array` | - | Suppliers impacted or notified downstream (not the cause: that is origin_supplier_id). |
| `affected_essential_asset_ids` | `array` | - | Essential assets affected. Use list_essential_assets. |
| `affected_support_asset_ids` | `array` | - | Support assets affected. Use list_support_assets. |
| `affected_site_ids` | `array` | - | Sites affected. Use list_sites. |
| `affected_activity_ids` | `array` | - | Business activities halted. Use list_activities. |
| `threat_ids` | `array` | - | The threats that materialised. Use list_threats. |
| `exploited_vulnerability_ids` | `array` | - | Vulnerabilities exploited. Use list_vulnerabilities. |
| `realised_risk_ids` | `array` | - | Registered risks that actually materialised. Use list_risks. |
| `linked_requirement_ids` | `array` | - | Controls in play. Use list_requirements. |

## `update_incident_evidence`

Update an existing incident evidence

Requires `incidents.evidence.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `incident_id` | `string` | - | UUID of the parent incident. Use list_incidents to get valid IDs. |
| `title` | `string` | - | Name of the artefact. |
| `description` | `string` | - | What the artefact is and why it matters. |
| `evidence_type` | `string` | - | Kind of artefact. |
| `tlp` | `string` | - | Traffic Light Protocol handling caveat. Defaults to red. |
| `collected_at` | `string` | - | Acquisition date-time (ISO 8601). Frozen once the item is sealed. |
| `collected_by_id` | `string` | - | UUID of the user who acquired it. Frozen once sealed. Use list_users. |
| `collection_method` | `string` | - | How it was acquired. Frozen once sealed. |
| `source_support_asset_id` | `string` | - | UUID of the support asset the artefact came from. Use list_support_assets. |
| `source_description` | `string` | - | Free-text description of the source when no asset is recorded. |
| `content_hash` | `string` | - | Hex digest of the artefact. Frozen once sealed. Never assert a verification verdict by writing here: call verify_evidence_integrity. |
| `hash_algorithm` | `string` | - | Digest algorithm the content hash was measured with. Frozen once sealed. |
| `original_filename` | `string` | - | Filename the artefact was acquired under. |
| `file_size` | `integer` | - | Size of the artefact in bytes. |
| `storage_location` | `string` | - | Where the artefact actually is, for an item registered by reference. |
| `legal_hold` | `boolean` | - | Under legal hold: destruction is refused while set. |
| `retention_until` | `string` | - | Retention expiry date (ISO 8601 date). |
| `admissibility_notes` | `string` | - | Notes bearing on the artefact's admissibility. |

## `update_incident_notification`

Update an existing incident notification

Requires `incidents.notification.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `incident_id` | `string` | - | UUID of the parent incident. Use list_incidents to get valid IDs. |
| `regime` | `string` | - | The regulatory regime this obligation arises under. |
| `recipient_kind` | `string` | - | Who the notification is owed to. |
| `authority_id` | `string` | - | UUID of the body the filing goes to. Use list_reporting_authoritys. |
| `recipient_stakeholder_id` | `string` | - | UUID of the stakeholder recipient. Use list_stakeholders. |
| `recipient_supplier_id` | `string` | - | UUID of the supplier recipient. Use list_suppliers. |
| `recipient_name` | `string` | - | Free-text recipient, when it is none of the three modelled kinds. |
| `obligation_reference` | `string` | - | The article the duty comes from, snapshotted from the template. |
| `content_requirements` | `string` | - | What the law requires this filing to contain, snapshotted from the template. |
| `clock_anchor` | `string` | - | Which incident timestamp the statutory clock runs from. Frozen once the obligation has been filed. |
| `deadline_hours` | `integer` | - | Hours from the anchor to the deadline. Frozen once filed. |
| `no_fixed_deadline` | `boolean` | - | The regime imposes no fixed deadline. |
| `depends_on_id` | `string` | - | UUID of the obligation whose first filing anchors this one's clock. Use list_incident_notifications. |
| `channel` | `string` | - | How the notification is transmitted. |
| `content` | `string` | - | The text that is filed. Frozen once the obligation has been sent: an amendment is a further filing. |
| `decision_rationale` | `string` | - | Why the obligation is required, or why it is not. The decision itself is a transition, not a field write. |
| `acknowledgement_reference` | `string` | - | Reference the recipient returned on acknowledgement. |
| `acknowledged_at` | `string` | - | When the recipient acknowledged (ISO 8601). |
| `proof_evidence_id` | `string` | - | UUID of the evidence item holding the proof of filing. Use list_incident_evidences. |

## `update_incident_response_action`

Update an existing incident response action

Requires `incidents.incident.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `incident_id` | `string` | - | UUID of the parent incident. Use list_incidents to get valid IDs. |
| `action_type` | `string` | - | Which ISO 27035 response step this action belongs to. |
| `title` | `string` | - | What is being done, in the imperative. |
| `description` | `string` | - | The command to run, the runbook section, the person to call. |
| `status` | `string` | - | Operational progress. A plain status column, not a lifecycle state. |
| `owner_id` | `string` | - | UUID of the user accountable for the step. Use list_users. |
| `performed_by_id` | `string` | - | UUID of the user who actually executed it. Use list_users. |
| `due_at` | `string` | - | Due date-time (ISO 8601). Drives the escalation sweep. |
| `started_at` | `string` | - | Execution start (ISO 8601). |
| `completed_at` | `string` | - | Execution end (ISO 8601). |
| `outcome` | `string` | - | What the action actually achieved. A containment step marked done with no stated outcome is not evidence of containment. |
| `effectiveness` | `string` | - | Whether the step worked, assessed during the post-incident review (A.5.27). |

## `update_incident_response_plan`

Update an existing incident response plan

Requires `incidents.response_plan.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | Name of the response plan. |
| `purpose` | `string` | - | What the plan is for. |
| `procedure` | `string` | - | Response procedure (HTML rich text) |
| `classification_scale` | `string` | - | What low / medium / high / critical mean in this organisation's terms (HTML rich text) |
| `escalation_matrix` | `string` | - | Who is escalated to, at which severity, within which delay (HTML rich text) |
| `reporting_channels` | `string` | - | How events and weaknesses are reported, including the anonymous channel A.6.8 requires (HTML rich text) |
| `evidence_procedure` | `string` | - | Identification, collection, acquisition and preservation of evidence (A.5.28) (HTML rich text) |
| `lessons_learned_procedure` | `string` | - | How knowledge gained from incidents strengthens controls (A.5.27) (HTML rich text) |
| `applicable_regimes` | `array` | - | Regulatory regimes this plan is built to satisfy. Triage instantiates one notification obligation per applicable regime. |
| `owner_id` | `string` | - | UUID of the plan owner. Use list_users to get valid IDs. |
| `approved_by_id` | `string` | - | UUID of the approver. Use list_users to get valid IDs. |
| `approved_at` | `string` | - | Approval date (ISO 8601 date). |
| `effective_from` | `string` | - | Date the plan takes effect (ISO 8601 date). |
| `review_date` | `string` | - | Next review date (ISO 8601 date). |
| `scope_ids` | `array` | - | Scopes this plan covers (RG-01). |
| `responsible_role_ids` | `array` | - | Roles accountable under this plan. Use list_roles. |
| `linked_requirement_ids` | `array` | - | Requirements this plan satisfies. Use list_requirements. |

## `update_obligation_template`

Update an existing obligation template

Requires `incidents.response_plan.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | Name of the catalogue rule. |
| `authority_id` | `string` | - | UUID of the body the filing goes to. Use list_reporting_authoritys to get valid IDs. |
| `regime` | `string` | - | The regulatory regime this rule instantiates. |
| `recipient_kind` | `string` | - | Who the notification is owed to. |
| `legal_reference` | `string` | - | The article the duty comes from (e.g. 'GDPR Art. 33(1)'). |
| `content_requirements` | `string` | - | What the law requires the filing to contain. |
| `clock_anchor` | `string` | - | Which incident timestamp the statutory clock runs from. |
| `clock_hours` | `integer` | - | Hours from the anchor to the deadline (e.g. 72 for GDPR Art. 33). |
| `no_fixed_deadline` | `boolean` | - | The regime imposes no fixed deadline. Distinct from a clock that has simply not started. |
| `depends_on_regime` | `string` | - | The sibling regime whose first filing anchors this staged obligation. |
| `jurisdiction_country` | `string` | - | Country this rule applies in. |
| `min_severity` | `string` | - | Severity floor below which the obligation is not raised. |
| `requires_significant` | `boolean` | - | Only raised when the incident is NIS2-significant. |
| `requires_personal_data` | `boolean` | - | Only raised when personal data is involved. |
| `requires_high_risk` | `boolean` | - | Only raised when the breach is high risk to rights and freedoms. |
| `requires_cross_border` | `boolean` | - | Only raised when the incident is cross-border. |
| `controller_roles` | `array` | - | GDPR controller roles this rule applies to. |
| `applicable_categories` | `array` | - | Incident categories this rule applies to. Empty means all. |
| `order` | `integer` | - | Display / generation order within the catalogue. |

## `update_personal_data_breach`

Update an existing personal data breach

Requires `incidents.notification.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `incident_id` | `string` | - | UUID of the incident this breach record qualifies (one per incident). Use list_incidents. |
| `controller_role` | `string` | - | The organisation's GDPR role for this processing. |
| `controller_supplier_id` | `string` | - | UUID of the controller we act as processor for. Use list_suppliers. |
| `lead_authority_id` | `string` | - | UUID of the lead supervisory authority. Use list_reporting_authoritys. |
| `cross_border_eu` | `boolean` | - | Data subjects in more than one Member State are affected. |
| `nature` | `string` | - | Nature of the breach (GDPR Art. 33(3)(a)). |
| `data_categories` | `array` | - | Categories of personal data affected (free-form list). |
| `data_subject_categories` | `array` | - | Categories of data subject affected (free-form list). |
| `approximate_data_subjects` | `integer` | - | Approximate number of data subjects concerned. |
| `approximate_records` | `integer` | - | Approximate number of personal data records concerned. |
| `special_categories` | `boolean` | - | Art. 9 special-category data is involved. |
| `volume_is_estimate` | `boolean` | - | The two counts are estimates rather than measured figures. |
| `dpo_contact` | `string` | - | Contact point for the DPO (GDPR Art. 33(3)(b)). |
| `likely_consequences` | `string` | - | Likely consequences of the breach (GDPR Art. 33(3)(c)). |
| `measures_taken` | `string` | - | Measures taken or proposed (GDPR Art. 33(3)(d)). |
| `high_risk_to_rights` | `boolean` | - | High risk to the rights and freedoms of natural persons (GDPR Art. 34(1)). |
| `high_risk_justification` | `string` | - | Reasoning behind the high-risk verdict. |
| `article_34_exemption` | `string` | - | Ground relied on to omit the communication to data subjects (GDPR Art. 34(3)). |
| `article_34_exemption_justification` | `string` | - | Reasoning behind the Art. 34(3) exemption. |
| `register_entry_reference` | `string` | - | Reference of the matching entry in the Art. 33(5) internal breach register. |

## `update_post_incident_review`

Update an existing post incident review

Requires `incidents.review.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `incident_id` | `string` | - | UUID of the incident being reviewed (one review per incident). Use list_incidents. |
| `response_plan_id` | `string` | - | UUID of the response plan the incident was handled under. Use list_incident_response_plans. |
| `scheduled_date` | `string` | - | Date the review is scheduled for (ISO 8601 date). |
| `facilitator_id` | `string` | - | UUID of the user facilitating the review. Use list_users. |
| `root_cause_method` | `string` | - | Root cause analysis method used. |
| `root_cause` | `string` | - | The root cause as determined by the analysis. |
| `contributing_factors` | `string` | - | Factors that contributed without being the root cause. |
| `detection_gap` | `string` | - | Why detection took as long as it did. |
| `containment_assessment` | `string` | - | How well containment worked. |
| `what_went_well` | `string` | - | What the response got right. |
| `what_failed` | `string` | - | What the response got wrong. |
| `recurrence_likelihood` | `string` | - | Likelihood the incident recurs. |
| `similar_incidents_checked` | `boolean` | - | Whether the register was checked for similar incidents (A.5.27). |
| `risk_reassessment_required` | `boolean` | - | A risk reassessment is owed. |
| `response_plan_update_required` | `boolean` | - | The response plan needs updating. |
| `training_required` | `boolean` | - | Training or awareness action is owed. |
| `effectiveness_review_date` | `string` | - | Date the effectiveness of the corrective actions is to be re-checked (ISO 8601 date). |
| `effectiveness_verdict` | `string` | - | ISO 27001 clause 10.2 d): did the corrective action actually work. |
| `effectiveness_reviewed_by_id` | `string` | - | UUID of the user who assessed effectiveness. Use list_users. |
| `effectiveness_notes` | `string` | - | Reasoning behind the effectiveness verdict. |
| `participant_ids` | `array` | - | Users who took part in the review. Use list_users. |
| `raised_finding_ids` | `array` | - | Findings raised by the review. Use list_findings. |
| `corrective_action_plan_ids` | `array` | - | Corrective action plans opened. Use list_action_plans. |
| `failed_control_ids` | `array` | - | Requirements whose control failed. Use list_requirements. |
| `control_to_strengthen_ids` | `array` | - | Requirements whose control must be strengthened. Use list_requirements. |
| `identified_risk_ids` | `array` | - | Risks identified by the review. Use list_risks. |
| `identified_vulnerability_ids` | `array` | - | Vulnerabilities identified by the review. Use list_vulnerabilities. |
| `isms_change_ids` | `array` | - | ISMS changes triggered by the review. |

## `update_reporting_authority`

Update an existing reporting authority

Requires `incidents.response_plan.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `name` | `string` | - | Full name of the body. |
| `short_name` | `string` | - | Common abbreviation (e.g. CNIL, ANSSI). |
| `authority_type` | `string` | - | Kind of body. |
| `primary_regime` | `string` | - | The regime this body is primarily the recipient for. |
| `additional_regimes` | `array` | - | Further regimes this body also receives filings under. |
| `jurisdiction_country` | `string` | - | Country whose jurisdiction the body exercises. |
| `portal_url` | `string` | - | URL of the online filing portal. |
| `contact_email` | `string` | - | Contact email address. |
| `contact_phone` | `string` | - | Contact phone number. |
| `notification_language` | `string` | - | Language filings must be written in (e.g. fr, en). |
| `procedure` | `string` | - | How a filing is actually made with this body. |

## `update_security_event`

Update an existing security event

Requires `incidents.event.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the object to update |
| `title` | `string` | - | Short title of the observation. |
| `description` | `string` | - | What was observed, in the reporter's own words. Never rewritten on promotion. |
| `event_class` | `string` | - | What kind of occurrence this is. Governs which promotion targets are legal. |
| `category` | `string` | - | Provisional classification, refined on promotion. |
| `detection_source` | `string` | - | How the event came to light. |
| `source_reference` | `string` | - | SIEM alert id, ticket number or CERT bulletin reference. |
| `occurred_at` | `string` | - | Best estimate of when the occurrence started (ISO 8601). |
| `detected_at` | `string` | - | When it was detected (ISO 8601). Base of the mean-time-to-detect KPI. |
| `reported_at` | `string` | - | When it reached the incident response function (ISO 8601). |
| `is_anonymous` | `boolean` | - | Reported through the anonymous channel A.6.8 requires. |
| `reporter_id` | `string` | - | UUID of the reporting user. Use list_users to get valid IDs. |
| `reporter_label` | `string` | - | Identity of an external or non-user reporter: a customer, a researcher, an anonymous line. |
| `reported_by_supplier_id` | `string` | - | UUID of the supplier that notified us (NIS2 supply chain, GDPR Art. 33(2)). Use list_suppliers. |
| `duplicate_of_id` | `string` | - | UUID of the earlier security event this one repeats. Use list_security_events. |
| `assessed_by_id` | `string` | - | UUID of the user who performed the A.5.25 assessment. Use list_users. |
| `assessment_notes` | `string` | - | The reasoning behind the triage decision. An undocumented assessment is not an assessment. |
| `scope_ids` | `array` | - | Scopes this event belongs to (RG-01). A promoted incident inherits them. |
| `affected_support_asset_ids` | `array` | - | Support assets involved. Use list_support_assets. |
| `affected_essential_asset_ids` | `array` | - | Essential assets involved. Use list_essential_assets. |
| `affected_site_ids` | `array` | - | Sites involved. Use list_sites. |

## `verify_evidence_integrity`

Re-measure an evidence artefact and append the result to its chain of custody. Returns one of three outcomes, which are never collapsed into each other: 'match' (the artefact was read and its digest equals the recorded content hash), 'mismatch' (it was read and the digest differs, which is a permanent chain-of-custody break) and 'not_verifiable' (the item is registered by reference, or the file is missing or unreadable, which is a claim about the storage and not about the artefact). The digest is measured, never asserted by the caller.

Requires `incidents.evidence.update`.

| Parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | `string` | yes | UUID of the evidence item. Use list_incident_evidences to get valid IDs. |
| `notes` | `string` | - | Optional note recorded on the custody row (why the check was run, who asked for it). |
