"""First-run onboarding: bootstrap an un-initialised Cairn instance.

While the instance has no users (a brand-new database), the onboarding flow
lets an operator either create the first super-admin ("start from scratch") or
load the demo dataset ("start with sample data"). It also surfaces the database
migration state. Everything here is pre-authentication and one-time only: once
any user exists, the flow is closed.
"""
