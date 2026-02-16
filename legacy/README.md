# Legacy

В этой папке хранятся старые (legacy) CLI-версии проекта `ani-cli-ru` и вспомогательные файлы.
Основной и рекомендуемый способ запуска сейчас - TUI-приложение через `ui_tui.py` в корне проекта, а `legacy` оставлен как архив старых скриптов.

## Содержимое

- `ani-cli-ru` - POSIX `sh` скрипт, старая CLI-реализация для Linux/macOS.
- `ani-cli-ru.ps1` - версия на PowerShell (рабочий CLI-скрипт для Windows).
- `ani-cli-ru.cmd` - wrapper для Windows `cmd`; запускает файл `ani-cli-ru.ps1`.
- `ani-cli.sh` - упрощенный старый shell-прототип (минимальные примеры работы с API).
- `main.py` - старый пример API-интеграции на Python (`requests`, `argparse`).
- `CONTRIBUTING.md` - правила контрибьюта для legacy shell-скриптов.
- `hacking.md` - заметки по архитектуре/разработке legacy-части.
- `py` - пустой placeholder-файл.

## Когда использовать

- Если нужно проверить или сравнить поведение старого CLI.
- Если нужно отладить логику shell/PowerShell скриптов.
- Как reference при миграции с исторического кода на новый TUI.

## Быстрый запуск

PowerShell:

```powershell
./legacy/ani-cli-ru.ps1 --help
```

CMD wrapper:

```bat
legacy\ani-cli-ru.cmd --help
```

POSIX shell:

```sh
sh ./legacy/ani-cli-ru --help
```

## Примечание

`legacy` не является основной активно развиваемой частью проекта. Новые функции и исправления в первую очередь вносятся в TUI-код в корне проекта.
