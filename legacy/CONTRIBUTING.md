# Contributing to ani-cli-ru

Thanks for contributing.

## Requirements

- Keep changes POSIX `sh` compatible
- Keep dependency footprint small
- Preserve bilingual UX (`ru` and `en`)
- Maintain support for `mpv`, `vlc`, and `iina`

## Workflow

1. Fork and create a branch
2. Make focused commits
3. Run checks locally
4. Open a pull request with clear context

## Local Checks

```sh
sh -n ani-cli-ru
./ani-cli-ru --help
./ani-cli-ru --version
```

Optional smoke test:

```sh
ANI_CLI_DOWNLOAD_DIR=/tmp/ani-cli-ru-test-dl ./ani-cli-ru -d -e 1 "9329"
```

## Pull Request Guidelines

Include:

- What changed
- Why it changed
- How it was tested
- Any behavior changes in CLI flags or env vars

## Reporting Issues

When filing bugs, include:

- OS and shell version
- Command used
- Expected behavior
- Actual behavior
- Logs/errors (without secrets)

## License

By contributing, you agree that your contributions are licensed under GPL-3.0.
