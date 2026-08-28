# Technical documentation

For whoever installs, configures, secures and operates a Cairn deployment. It
stops at the boundary of the code : how to run the platform, not how to change
it. Changing it is the [SDK](../sdk/README.md).

| Page | Contents |
| --- | --- |
| [Architecture](architecture.md) | The stack, the apps, how a request is served, the cross-cutting patterns every module inherits |
| [Installation](installation.md) | Docker from source, the published image, pure Python with mise for debugging |
| [Configuration](configuration.md) | Every environment variable that matters, and the ones you must not leave at their default |
| [Security](security.md) | Authentication, permissions, tenancy, the audit trail, and what an operator still has to do |
| [Operations](operations.md) | Scheduled commands, backups, upgrades, logs, health |
| [Internationalisation](internationalization.md) | The bilingual contract and how a translated string travels |
| [Testing](testing.md) | Running the suite, how it is organised, what CI enforces |
| [Contributing](contributing.md) | Branch, commit and pull-request conventions |
| [Documentation](documentation.md) | How this documentation set is built, checked and published |
| [Release process](release-process.md) | Tagging a version, the image, the GitHub release, the wiki |

## Version

The running version is read at startup from `/etc/app-version` (written into the
image at build time) or from `version.txt`, and falls back to `dev`. It is shown
in the interface footer, so a screenshot of a deployment always says which build
produced it.
