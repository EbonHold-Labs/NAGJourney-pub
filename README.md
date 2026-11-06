# NAG Journey — public downloads

Official public release channel for **NAG Journey**, the World of Warcraft addon
for gear upgrades, quest rewards and navigation.

## Download and install

Open [Releases](https://github.com/EbonHold-Labs/NAGJourney-pub/releases) and
download the `NAGJourney-<version>.zip` asset for the version you want. GitHub's
automatically generated **Source code** archives are not addon packages.

Extract both folders into your game client's `Interface/AddOns` directory:

```text
Interface/AddOns/
  NAGJourney/
  NAGJourneyTerrainData/
```

Keep both folders together. `NAGJourneyTerrainData` supplies the navigation data
and loads when needed. The current release target is **WoW Forever**
(`_forever_`, Interface 16001).

Support for this channel is prepared for NAG Helper's **Addon > NAG Journey**
page and becomes available with a Helper update that includes it. **Release**
offers stable versions; **Beta** also offers beta previews. Helper checks package
size and SHA-256 before installation.

## Availability

Only uploaded addon ZIPs on published releases are installable. Until the first
package is published here, there is no public download and Helper shows
**Not published**. Creating this channel does not itself publish an addon build.

## Reports

Use the question-mark button in NAG Journey to prepare an issue report, with
NAG Helper running and signed in for delivery. This repository hosts downloads;
issue reports continue through Journey's existing reporting service.

## Package and license information

Published addon packages contain the Lua runtime source, `LICENSE`,
`THIRD_PARTY.md` and the applicable third-party license/provenance notices.
NAG Journey is distributed under **GPL-3.0-or-later**; see the license and
third-party notices included with the release for details.

Maintainers publish `NAGJourney-<version>.zip` with the same version in both
addon TOCs. Stable tags use `v<major>.<minor>.<patch>`; beta tags use
`v<major>.<minor>.<patch>-beta<number>` and are marked as prereleases.

## CurseForge publishing

Set `CURSEFORGE_PROJECT_ID` as a repository Actions variable and
`CURSEFORGE_API_TOKEN` as a repository Actions secret. The token must belong
to a CurseForge account that can upload files to that project.

Publish the GitHub release from the current `main` commit in this repository
after attaching the ZIP, manifest and SHA-256 file to its draft. The
**Publish release to CurseForge** workflow verifies those assets, resolves the
Forever game version from the packaged TOCs, and submits the same ZIP and
release notes to CurseForge. Stable and beta tags retain their release types.
The workflow logs the CurseForge file ID once the submission is accepted for
review. If both settings are absent, the workflow reports that uploads are
disabled.

For an existing release, run the workflow from `main` with its tag and leave
**verify_only** enabled to validate the assets and available configuration.
For a one-time upload, run it with **verify_only** disabled after checking
whether the file is already on CurseForge. A real upload creates a
`curseforge-upload/<tag>` Git tag before submission to prevent duplicates.
If submission fails after reservation, check the project's Files tab and the
workflow log. Remove that reservation tag only after confirming CurseForge
has no file for the release, then dispatch again.
