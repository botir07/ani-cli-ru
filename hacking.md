# hacking.md

## Overview

`ani-cli-ru` is a multi-platform anime streaming tool with:

1. **POSIX shell script** (`ani-cli-ru`) - Terminal-based CLI
2. **PowerShell script** (`ani-cli-ru.ps1`) - Windows CLI
3. **Python GUI** (`main.py`) - Tkinter-based graphical interface

## GUI Architecture (main.py)

### Classes

1. **AniLibriaClient** - API client for AniLibria
   - Supports multi-language dubbing selection
   - Available dubbing: RU, EN, UK, TR + subtitles
   
2. **HistoryStore** - Local history persistence
   - Stores watched releases in JSON format
   - Max 50 items (configurable)

3. **AniCliRuGui** - Main GUI application
   - Tkinter-based interface
   - Dark/light theme support
   - Multi-language UI (ru/en)
   - Multi-language dubbing selection

### Dubbing System

The GUI supports multiple dubbing languages through Kodik/AniQit integration:

```python
DUB_LANGUAGES = [
    {"code": "ru", "name": "Русский (AniLibria)", "type": "dub"},
    {"code": "en", "name": "English (AniQit)", "type": "dub"},
    {"code": "uk", "name": "Українська (AniQit)", "type": "dub"},
    {"code": "tr", "name": "Türkçe (AniQit)", "type": "dub"},
    {"code": "sub_ru", "name": "Русские субтитры", "type": "sub"},
    {"code": "sub_en", "name": "English subtitles", "type": "sub"},
]
```

### Key Methods

- `_apply_dubbing()` - Apply selected dubbing language
- `_update_watch_mode_options()` - Update playback options based on dubbing
- `_resolve_kodik_dub_stream()` - Resolve foreign dubbing stream from Kodik
- `_pick_kodik_dub_translation()` - Select dubbing by language keywords

### Stream Resolution Flow

1. **RU Dubbing**: Direct HLS from AniLibria CDN
2. **EN/UK/TR Dubbing**: 
   - Fetch Kodik player page
   - Parse available translations
   - Select matching dubbing by language keywords
   - Resolve stream URL through `/ftor` endpoint
3. **Subtitles**:
   - Enable translations on Kodik
   - Find subtitles translation
   - Resolve subtitle stream

## API Details

Default API base:
- `https://api.anilibria.app/api/v1`

Key endpoints:
- `app/search/releases` - Search anime
- `anime/releases/latest` - Latest releases
- `anime/releases/random` - Random picks
- `anime/releases/{id}` - Release details with episodes

## Local Development

### Running GUI

```sh
cd ani-cli-ru
python main.py
```

### Syntax Check

```sh
python -m py_compile main.py
```

### Dependencies

```sh
pip install requests
```

## Coding Standards

- Python 3.8+ compatible
- Type hints where beneficial
- Clear error messages with context
- Async operations for network calls
- Thread-safe GUI updates via `after()`

## Testing Checklist

- [ ] Search functionality (RU/EN queries)
- [ ] Dubbing selection (all 6 options)
- [ ] Episode selection
- [ ] Stream playback (RU HLS + External)
- [ ] Dark/light theme toggle
- [ ] History persistence
- [ ] Recommendations loading

---

*Last updated: 2026-03-06*
