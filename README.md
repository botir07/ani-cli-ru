# ani-cli-ru (TUI)

`ui_tui.py` — удобная точка входа для запуска TUI-приложения.
Основной код находится в `src/anicliru_tui/`.

## Структура проекта

```text
ani-cli-ru-main/
  RUN.bat                  # запуск в Windows (двойной клик)
  ui_tui.py                # root-launcher (совместимость со старым запуском)
  src/
    anicliru_tui/
      __init__.py
      __main__.py
      app.py               # основная логика TUI
  downloads/               # загруженные эпизоды (создается автоматически)
  legacy/                  # старые CLI-скрипты и вспомогательные файлы
    ani-cli-ru
    ani-cli-ru.ps1
    ani-cli-ru.cmd
    ani-cli.sh
    main.py
    py
    CONTRIBUTING.md
    hacking.md
```

## Основные возможности

- Поиск аниме по RU/EN названию
- Список эпизодов с выбором в UI
- `Enter` на эпизоде: запуск плеера
- Переключение качества (`q`)
- Авто fallback качества, если выбранное недоступно
- Скачивание эпизода (`d`)
- Короткий `Status` в информационной панели

## Зависимости

- Python 3.10+
- `textual`
- `httpx`
- Опционально:
  - плеер (`mpv`, `vlc`, MPC, PotPlayer)
  - `ffmpeg` (скачивание сразу в `.mp4`)

Установка:

```bash
py -m pip install textual httpx
```

## Запуск

Вариант 1 (рекомендуется):

```bat
RUN.bat
```

Вариант 2:

```bash
py ui_tui.py
```

## Запуск в разных терминалах

### Windows PowerShell

```powershell
# пример
cd C:\Users\<username>\Desktop\ani-cli-ru-main
py -m pip install -r requirements.txt
py ui_tui.py
```

### Windows CMD

```bat
REM пример
cd /d C:\Users\<username>\Desktop\ani-cli-ru-main
py -m pip install -r requirements.txt
py ui_tui.py
```

### Linux terminal (bash/zsh)

```bash
cd /path/to/ani-cli-ru-main
python3 -m pip install -r requirements.txt
python3 ui_tui.py
```

### macOS terminal (zsh)

```bash
cd /path/to/ani-cli-ru-main
python3 -m pip install -r requirements.txt
python3 ui_tui.py
```

## Управление

- `Enter`: воспроизвести выбранный эпизод
- `d`: скачать выбранный эпизод
- `q`: сменить качество
- `[` / `]`: предыдущий / следующий эпизод
- `Ctrl+C`: выход

## Переменные окружения

- `ANI_CLI_API_BASE` (по умолчанию `https://anilibria.top/api/v1`)
- `ANI_CLI_QUALITY` (по умолчанию `best`)
- `ANI_CLI_PLAYER` (по умолчанию `mpv`)
- `ANI_CLI_DOWNLOAD_DIR` (по умолчанию `./downloads`)

## Лицензия

GPL-3.0. См. `LICENSE`.
