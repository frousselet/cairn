# Ask Cairn

An optional natural-language question mode in the command palette. Ask "Which
decisions were made at the last management review?" and get an answer that
**cites real records**.

It is **off by default**, and your administrator has to enable it deliberately.

## What it does

Type a question into the command palette instead of a search term. Cairn routes
it to a set of read-only data tools, runs them, and returns two things:

**The records.** Real rows from your database, each linking to the record it
came from. These are the answer.

**A summary sentence**, written by the configured language model and clearly
labelled as AI-generated. It is a convenience over the records, not a substitute
for them.

The distinction matters. Verify the summary against the records it cites,
particularly for anything that will end up in a report or a decision. The
records are facts from your database; the sentence is a model's reading of them.

## What it cannot do

**It cannot widen your access.** Every data access inside the loop runs through
the ordinary read tools with your permissions and your scopes. It can only cite
records you were already allowed to read. Two people asking the same question can
get different answers, and that is the tenancy model working.

**It cannot change anything.** The tools it can reach are read-only.

## Semantic search

Where enabled, requirement search becomes meaning-based rather than
keyword-based, and works across languages : searching in French finds a
requirement written in English about the same control.

This needs an index, which your administrator builds and refreshes. If semantic
search seems to be missing results, a stale index is the usual cause.

## Feedback

Every answer has a thumbs up and thumbs down. Use them.

Administrators can review and export the feedback under Administration -> Ask
Cairn -> Feedback, together with the original question and what the model
returned. A thumbs down on a wrong answer is what makes the next version better;
it is not a complaint that goes nowhere.

## What leaves the platform

This is the part to read before asking your administrator to turn it on.

With a **third-party provider** (Mistral, OpenAI, Anthropic), your question text
and the compact record fields used for routing are sent to that provider. That
is a data protection decision, not a preference.

With **Ollama**, pointed at your own instance, nothing leaves your
infrastructure.

The provider is a deployment choice. The
[assistant specification](../specs/assistant/README.md) describes each option
and its data-egress properties in detail.

## When it is unavailable

If the assistant is disabled or its provider is unreachable, the question mode
reports it plainly rather than returning a degraded answer. Ordinary search and
navigation are unaffected : Ask Cairn is a layer on top, never a dependency.

## Its name

The assistant's name is configurable in the company settings. "Ask Cairn" is the
default; an organisation that prefers its own name for it can say so.
