<<<<<<< HEAD
# Development Guide

## API Documentation
- Details about the API endpoints and usage.

## Testing Instructions
- Instructions on how to run tests for the project.

## Contribution Guidelines
- Guidelines for contributing to the project.
  - Fork the repository.
  - Create a new branch for your feature or fix.
  - Make your changes and commit them.
  - Submit a pull request for review.


---

*Last updated: 2026-02-12*
=======
# hacking.md

## Overview

`ani-cli-ru` is a single POSIX shell entrypoint (`./ani-cli-ru`) with function-based modules inside one file.

Main layers:

1. CLI parsing and configuration
2. Localization (`ru` / `en`) and user messaging
3. API adapter (`v1` default, `v3` compatibility)
4. Interactive selection (fzf/rofi)
5. Playback/download execution
6. History storage

## Design Goals

- POSIX `sh` compatibility (no bash-only syntax)
- Minimal external dependencies (`curl`, `jq`, `fzf`/`rofi`)
- Predictable option handling and validation
- Clear fallback behavior for player/downloader/API variants

## Important Functions

- `parse_args`: parses CLI options and query text
- `detect_api_mode`: selects API adapter (`auto|v1|v3`)
- `search_titles` / `fetch_title`: adapter-aware data retrieval
- `get_episodes`: normalizes episode list from API payload
- `get_stream_url`: normalizes stream URL selection by quality/type
- `resolve_player`: player detection and fallback
- `append_history` / `show_history` / `clear_history`: history lifecycle

## API Details

Default API base:

- `https://api.anilibria.app/api/v1`

Compatibility mode:

- `ANI_CLI_API_BASE=https://api.anilibria.tv/v3`
- `ANI_CLI_API_MODE=v3`

The script normalizes the differences between v1 and v3 payloads so downstream logic stays the same.

## Local Development

Run syntax checks:

```sh
sh -n ani-cli-ru
```

Show help/version:

```sh
./ani-cli-ru --help
./ani-cli-ru --version
```

Test history in temp directory:

```sh
ANI_CLI_HIST_DIR=/tmp/ani-cli-ru-test ./ani-cli-ru -D
ANI_CLI_HIST_DIR=/tmp/ani-cli-ru-test ./ani-cli-ru -l
```

Smoke test without launching player:

```sh
ANI_CLI_DOWNLOAD_DIR=/tmp/ani-cli-ru-test-dl ./ani-cli-ru -d -e 1 "9329"
```

## Coding Standards

- Keep code POSIX sh-safe
- Quote variables unless intentional word splitting
- Validate user inputs before API or player calls
- Prefer small, focused functions
- Avoid parsing JSON with `sed`; use `jq`
>>>>>>> b7c7c13 (ani-cli)
