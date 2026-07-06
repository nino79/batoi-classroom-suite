# assets/

Shared branding assets consumed by BCS components — primarily [Boot Manager](../boot-manager/)'s themeable menu (`BM-004`), and potentially Builder's splash/branding during golden-image customisation.

## Subdirectories

| Directory | Contents |
|---|---|
| [backgrounds/](backgrounds/) | Boot menu and splash-screen background images. |
| [fonts/](fonts/) | Fonts used in boot-time UI, chosen for Valencian/Spanish character support (`BM-007`). |
| [icons/](icons/) | Icons for boot menu entries (normal boot, maintenance boot, recovery, etc.). |
| [logos/](logos/) | CIPFP Batoi / LliureX / project branding marks. |

## Design Constraint

Per [BM-004](../SPECIFICATION.md#21-boot-manager), Boot Manager must be able to swap every asset category here for a different centre's branding without a code change. Anything added to this directory should be referenced by Boot Manager configuration, not hard-coded by path in component logic.

## Status

Directories exist as placeholders; no assets are populated yet. This is expected during the current [documentation-only phase](../ROADMAP.md) — actual brand assets will be contributed alongside Boot Manager's Phase 1 implementation.
