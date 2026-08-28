# Getting started

## First run

The first time you open a fresh Cairn, it does not show a login form. It shows a
**first-run screen** that reports the state of the database and offers two ways
forward.

**Start from scratch** is a two-step wizard : configure your company, then
create the first administrator account. Nothing is written until both steps are
complete, so an interrupted setup leaves no half-configured instance behind.

**Start with sample data** loads the Voltara Energy demo dataset behind a
progress bar and signs you in. It is the fastest way to see what a populated
Cairn looks like, and the right choice for an evaluation. It is not a starting
point for real data : the demo records are fictional and mixed throughout.

An administrator can also be created from the command line instead
(`python manage.py createsuperuser`), which is the path an automated deployment
usually takes.

## Signing in

Your identifier is your **email address**. There is no separate username.

Two things are worth setting up on day one.

**A passkey.** Under your profile, register a passkey and you can sign in with
your device's biometrics or PIN instead of a password. It is phishing-resistant
and, in Cairn, sufficient on its own.

**Your language and theme.** Cairn is bilingual, English and French. Your choice
is stored on your account, so it follows you to any device rather than living in
a browser cookie. The theme follows your operating system by default and can be
pinned to light or dark.

After five failed password attempts an account locks for fifteen minutes. If you
are locked out and cannot wait, an administrator can unlock you.

## The shape of the interface

Every screen has the same three parts.

**The sidebar**, on the left, is the module navigation. It is grouped by domain :
Governance, Assets, Risk management, Compliance, Incidents, and Administration
for those who have it.

**The header** carries global search, the command palette, notifications and
your account menu.

**The page** itself. Lists on the left of a detail page, metadata on the right :
the layout is consistent enough that once you can read one entity's detail page,
you can read all of them.

## Two things that decide what you see

Before you conclude something is missing, check these, in this order.

**Your permissions.** Cairn does not grey out what you cannot reach; it does not
show it. A menu entry you lack permission to read is simply absent. If a
colleague describes a screen you cannot find, the difference is usually a group
membership, not a bug.

**Your scopes.** Records are filtered to the organisational perimeters you are
assigned. Two people can look at the same risk register and honestly see
different counts. This is the tenancy model working, not a synchronisation
problem. See [Scopes](organisational-context.md#scopes).

## The first hour

If you are setting up a real instance, this order saves rework, because each
step is what the next one attaches to.

1. **Company settings.** Name, logo, accent colour. Administration -> Company.
2. **At least one scope.** Everything else attaches to a perimeter, and a record
   created before any scope exists has nowhere to live.
3. **Users and groups.** Invite the team; an invitation creates an account with
   no password and sends a single-use activation link.
4. **A framework.** Import ISO 27001, GDPR or your own from Excel. This is what
   gives compliance something to measure against.
5. **Assets.** Essential assets first (what the business actually depends on),
   then the support assets that carry them.
6. **Risk criteria, then a risk assessment.** The criteria define the scales, so
   they come first : changing them later does not rewrite scores already given.

Nothing here is irreversible, but this order means less of it has to be redone.

## Where to go next

[Finding your way](finding-your-way.md) covers search, the command palette and
the tasks board, which are what make the platform quick rather than merely
complete.
