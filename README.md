<<<<<<< HEAD
# ani-cli

 ani-cli is a command-line interface (CLI) for managing anime and manga.

## Features
- Easy to use command-line interface
- Supports searching for anime and manga
- Provides information like descriptions, ratings, and more
- Lightweight and fast

## Installation
To install ani-cli, follow these steps:
1. Make sure you have Go installed on your system.
2. Clone the repository:
   ```bash
   git clone https://github.com/botir07/ani-cli-ru.git
   cd ani-cli-ru
   ```
3. Build the project:
   ```bash
   go build
   ```
4. Move the binary to your PATH:
   ```bash
   mv ani-cli /usr/local/bin/
   ```

## Usage
Once installed, you can start using ani-cli by typing `ani-cli` in your terminal.

### Basic Command Structure
```bash
ani-cli [options] [command] [arguments]
```

## Examples
- Search for an anime:
  ```bash
  ani-cli search "Attack on Titan"
  ```
- Get details for a specific anime:
  ```bash
  ani-cli info "Attack on Titan"
  ```

## API Information
ani-cli interacts with public APIs to fetch data. Ensure you adhere to their usage limits and guidelines when using this tool.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.
=======
# ani-cli-ru

`ani-cli-ru` is a POSIX `sh` command-line tool to search, stream, and download Russian anime releases from AniLibria directly from the terminal.

## Features

- Search anime by Russian or English names
- Stream episodes with `mpv`, `VLC`, or `IINA`
- Download episodes with `aria2c` or `wget`
- Bilingual UI: Russian (`ru`) and English (`en`)
- Episode selection (`-e`) and episode ranges (`-r`)
- Quality selection: `best`, `worst`, `360p`, `480p`, `720p`, `1080p`
- Watch history view and cleanup
- Works on Linux, macOS, WSL, and Termux-compatible setups

## Dependencies

Required:

- `sh` (POSIX shell)
- `curl`
- `jq`

Interactive menu:

- `fzf` (default) or `rofi` (`--rofi`)

Playback:

- `mpv` (default), `vlc` (`--vlc`), or `iina` (macOS)

Download mode:

- `aria2c` (preferred) or `wget`

## Installation

```sh
git clone https://github.com/botir07/ani-cli-ru.git
cd ani-cli-ru
chmod +x ani-cli-ru
```

Optional system-wide install:

```sh
sudo install -m 0755 ani-cli-ru /usr/local/bin/ani-cli-ru
```

## Usage

```sh
ani-cli-ru "атака титанов"
ani-cli-ru "attack on titan"
ani-cli-ru -q 720p "код гиас"
ani-cli-ru -e 5 "demon slayer"
ani-cli-ru -r 1-3 "one piece"
ani-cli-ru -d -r 1-3 "naruto"
ani-cli-ru --sub "your lie in april"
```

Language control:

```sh
ANI_CLI_LANG=ru ani-cli-ru "query"
ANI_CLI_LANG=en ani-cli-ru "query"
```

## CLI Options

- `-h`, `--help`: Show help
- `-v`, `--version`: Show version
- `-q`, `--quality Q`: Set quality (`best|worst|360p|480p|720p|1080p`)
- `-d`, `--download`: Download mode
- `-e`, `--episode N`: Play/download one episode
- `-r`, `--range N-M`: Play/download episode range
- `-l`, `--logview`: View history
- `-D`, `--delete`: Clear history
- `--lang ru|en`: Set UI language
- `--sub`: Request subtitles stream when available
- `--vlc`: Use VLC player
- `--rofi`: Use rofi menu instead of fzf

## Environment Variables

- `ANI_CLI_LANG`: `ru` or `en`
- `ANI_CLI_PLAYER`: `mpv`, `vlc`, `iina`, `mpv.exe`
- `ANI_CLI_QUALITY`: default quality
- `ANI_CLI_STREAM_TYPE`: `dub` or `sub`
- `ANI_CLI_DOWNLOAD_DIR`: download path
- `ANI_CLI_HIST_DIR`: history directory
- `ANI_CLI_LOG`: history logging (`1` or `0`)
- `ANI_CLI_EXTERNAL_MENU`: `fzf` or `rofi`
- `ANI_CLI_API_BASE`: AniLibria API base URL
- `ANI_CLI_API_MODE`: `auto`, `v1`, or `v3`

## API Notes

AniLibria `v3` is deprecated on the old endpoint. This project defaults to:

- `https://api.anilibria.app/api/v1`

You can still force v3-compatible mode manually:

```sh
ANI_CLI_API_BASE="https://api.anilibria.tv/v3" ANI_CLI_API_MODE=v3 ani-cli-ru "query"
```

## Development

See `hacking.md` for implementation details and workflow.

## Contributing

See `CONTRIBUTING.md`.

## License

GPL-3.0. See `LICENSE`.
>>>>>>> b7c7c13 (ani-cli)
