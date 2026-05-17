# Changelog

All notable changes to this project will be documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-05-18

Initial public release.

### Added
- Interactive CLI (`ghstars` with no args) and individual subcommands
  (`setup`, `fetch`, `list-lists`, `delete-lists`, `apply`, `settings`,
  `status`, `clear-credentials`).
- 32 built-in default categories (`presets.DEFAULT_CATEGORIES`).
- Custom categories via JSON file with full validation (name length,
  duplicates, GitHub's 32-list cap).
- Cookie-based authentication; credentials stored in
  `~/.config/ghstars/credentials.json` with mode 600.
- Star library dump via the official `/users/{user}/starred` REST endpoint.
- Resumable state per account in `~/.config/ghstars/accounts/<user>/state.json`.
- Configurable jitter + retry settings with safety warnings.
- Random Chrome desktop User-Agent via `fake-useragent`.
- 59 unit tests covering validators, credentials, parser, categoriser, state
  and settings round-trips.
- Comprehensive `README.md` with disclaimer + risk list.
- `PROPOSAL.md` asking GitHub to ship an official Stars Lists API.
