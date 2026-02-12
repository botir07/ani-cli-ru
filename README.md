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