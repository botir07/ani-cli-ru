from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import httpx
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, ListItem, ListView, Static


API_BASE = os.getenv("ANI_CLI_API_BASE", "https://anilibria.top/api/v1")
DEFAULT_QUALITY = os.getenv("ANI_CLI_QUALITY", "best")
PLAYER = os.getenv("ANI_CLI_PLAYER", "mpv")
DOWNLOAD_DIR = Path(os.getenv("ANI_CLI_DOWNLOAD_DIR", str(Path.cwd() / "downloads")))
QUALITY_ORDER = ["best", "1080p", "720p", "480p", "360p", "worst"]


@dataclass
class Title:
    id: str
    name_ru: str
    name_en: str
    year: Optional[int] = None
    description: str = ""


class AniLibriaClient:
    def __init__(self, base: str = API_BASE) -> None:
        self.base = base.rstrip("/")
        self.http = httpx.Client(timeout=20)

    def search(self, query: str) -> List[Title]:
        r = self.http.get(f"{self.base}/app/search/releases", params={"query": query})
        r.raise_for_status()
        data = r.json()

        items = data if isinstance(data, list) else (data.get("list") or data.get("data") or [])
        out: List[Title] = []
        for it in items:
            out.append(
                Title(
                    id=str(it.get("id", "")),
                    name_ru=(it.get("name", {}).get("main") or it.get("name_ru") or ""),
                    name_en=(it.get("name", {}).get("english") or it.get("name_en") or ""),
                    year=it.get("year") or it.get("season", {}).get("year"),
                    description=it.get("description") or "",
                )
            )
        return out

    def get_release(self, title_id: str) -> dict:
        r = self.http.get(
            f"{self.base}/anime/releases/{title_id}",
            params={
                "include": (
                    "id,name,episodes_total,"
                    "episodes.ordinal,episodes.hls_360,episodes.hls_480,"
                    "episodes.hls_720,episodes.hls_1080"
                )
            },
        )
        r.raise_for_status()
        return r.json()


def pick_episode_stream_url(episode: dict, quality: str) -> tuple[Optional[str], Optional[str]]:
    quality_order = {
        "1080p": ["hls_1080", "hls_720", "hls_480", "hls_360"],
        "720p": ["hls_720", "hls_1080", "hls_480", "hls_360"],
        "480p": ["hls_480", "hls_360", "hls_720", "hls_1080"],
        "360p": ["hls_360", "hls_480", "hls_720", "hls_1080"],
        "worst": ["hls_360", "hls_480", "hls_720", "hls_1080"],
        "best": ["hls_1080", "hls_720", "hls_480", "hls_360"],
    }
    key_to_quality = {
        "hls_1080": "1080p",
        "hls_720": "720p",
        "hls_480": "480p",
        "hls_360": "360p",
    }
    for key in quality_order.get(quality, quality_order["best"]):
        url = episode.get(key)
        if isinstance(url, str) and url.strip():
            return (url.strip(), key_to_quality.get(key))
    return (None, None)


def resolve_player() -> Optional[str]:
    if PLAYER and shutil.which(PLAYER):
        return PLAYER

    candidates = [
        "mpv.exe",
        "vlc.exe",
        "mpv",
        "vlc",
        "mpc-hc64.exe",
        "mpc-hc.exe",
        "mpc-be64.exe",
        "mpc-be.exe",
        "potplayer64.exe",
        "potplayer.exe",
    ]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    windows_paths = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files\mpv\mpv.exe",
        r"C:\Program Files (x86)\mpv\mpv.exe",
        r"C:\Program Files\MPC-HC\mpc-hc64.exe",
        r"C:\Program Files\MPC-HC\mpc-hc.exe",
        r"C:\Program Files\MPC-BE x64\mpc-be64.exe",
        r"C:\Program Files\MPC-BE\mpc-be.exe",
        r"C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe",
        r"C:\Program Files (x86)\DAUM\PotPlayer\PotPlayerMini.exe",
    ]
    for p in windows_paths:
        if Path(p).exists():
            return p
    return None


def play_url(url: str) -> str:
    player = resolve_player()
    if player:
        try:
            player_name = Path(player).name.lower()
            cmd = [player, url]
            if player_name.startswith("mpv"):
                cmd = [player, "--really-quiet", "--msg-level=all=no", url]
            elif "vlc" in player_name:
                cmd = [player, "--quiet", url]

            creationflags = 0
            if os.name == "nt":
                creationflags = (
                    getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    | getattr(subprocess, "DETACHED_PROCESS", 0)
                )

            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            time.sleep(0.7)
            code = proc.poll()
            if code is None or code == 0:
                return Path(player).name
        except Exception:
            pass

    if hasattr(os, "startfile"):
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return "default-windows-player"
        except Exception:
            pass

    if os.name == "nt":
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", url],
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return "windows-start"
        except Exception:
            pass

    webbrowser.open(url)
    return "default-browser"


def parse_episode_number(value: object) -> Optional[int]:
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    return None


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", name).strip()
    return cleaned or "anime"


def download_episode_stream(stream_url: str, title_name: str, episode_num: int, quality: str) -> tuple[str, str]:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    base_name = f"{sanitize_filename(title_name)}_ep{episode_num}_{quality}"

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        target_mp4 = DOWNLOAD_DIR / f"{base_name}.mp4"
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-y",
                "-loglevel",
                "error",
                "-i",
                stream_url,
                "-c",
                "copy",
                str(target_mp4),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        if proc.returncode == 0 and target_mp4.exists():
            return ("ffmpeg", str(target_mp4))

    target_m3u8 = DOWNLOAD_DIR / f"{base_name}.m3u8"
    with httpx.stream("GET", stream_url, follow_redirects=True, timeout=60) as resp:
        resp.raise_for_status()
        with target_m3u8.open("wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    return ("playlist", str(target_m3u8))


class AniCliRuTUI(App):
    CSS = """
    Screen { padding: 1; }
    #left { width: 50%; }
    #right { width: 50%; }
    ListView { height: 1fr; border: round $panel; }
    #episodes { height: 12; border: round $panel; }
    #info { height: 1fr; border: round $panel; padding: 1; }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("enter", "play", "Play"),
        ("d", "download", "Download"),
        ("q", "cycle_quality", "Quality"),
        ("[", "prev_episode", "Prev Ep"),
        ("]", "next_episode", "Next Ep"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.api = AniLibriaClient()
        self.titles: List[Title] = []
        self.selected: Optional[Title] = None
        self.quality = DEFAULT_QUALITY if DEFAULT_QUALITY in QUALITY_ORDER else "best"
        self.episode_map: dict[int, dict] = {}
        self.selected_episode: Optional[int] = None
        self.release_cache: dict[str, dict] = {}
        self.episode_numbers: List[int] = []
        self.status_message: str = "Ready"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="left"):
                yield Input(placeholder="Search anime (ru/en)...", id="search")
                yield ListView(id="results")
            with Vertical(id="right"):
                yield ListView(id="episodes")
                yield Static("Info panel", id="info")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search":
            q = event.value.strip()
            if q:
                self.search_and_render(q)

    def search_and_render(self, q: str) -> None:
        results = self.query_api(q)
        self.titles = results
        self.episode_map = {}
        self.selected_episode = None
        self.episode_numbers = []
        lv = self.query_one("#results", ListView)
        lv.clear()
        for t in results:
            label = f"{t.name_ru or t.name_en} ({t.year})" if t.year else (t.name_ru or t.name_en)
            lv.append(ListItem(Static(label)))
        if results:
            self.selected = results[0]
            self.load_episodes_for_selected()
            self.status_message = f"Found {len(results)} title(s)"
            self.render_info(self.selected)

    def query_api(self, q: str) -> List[Title]:
        try:
            return self.api.search(q)
        except Exception as e:
            self.status_message = f"Search error: {e}"
            if self.selected:
                self.render_info(self.selected)
            else:
                self.query_one("#info", Static).update(f"[ERROR]\n{e}")
            return []

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        idx = event.list_view.index
        if idx is None:
            return
        if event.list_view.id == "results" and 0 <= idx < len(self.titles):
            self.selected = self.titles[idx]
            self.load_episodes_for_selected()
            self.render_info(self.selected)
        elif event.list_view.id == "episodes":
            if 0 <= idx < len(self.episode_numbers):
                self.selected_episode = self.episode_numbers[idx]
                if self.selected:
                    self.status_message = f"Episode selected: {self.selected_episode}"
                    self.render_info(self.selected)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "episodes":
            return
        idx = event.list_view.index
        if idx is None or not (0 <= idx < len(self.episode_numbers)):
            return
        self.selected_episode = self.episode_numbers[idx]
        self.action_play()

    def load_episodes_for_selected(self) -> None:
        if not self.selected:
            self.episode_map = {}
            self.selected_episode = None
            return
        try:
            title_id = self.selected.id
            release = self.release_cache.get(title_id)
            if release is None:
                release = self.api.get_release(title_id)
                self.release_cache[title_id] = release
            episodes = release.get("episodes") or []
            ep_map: dict[int, dict] = {}
            for ep in episodes:
                n = parse_episode_number(ep.get("ordinal"))
                if n is not None:
                    ep_map[n] = ep
            self.episode_map = ep_map
            if not self.episode_map:
                self.episode_numbers = []
                self.selected_episode = None
                self.render_episode_list()
                return
            if self.selected_episode not in self.episode_map:
                self.selected_episode = sorted(self.episode_map.keys())[0]
            self.render_episode_list()
        except Exception:
            self.episode_map = {}
            self.episode_numbers = []
            self.selected_episode = None
            self.render_episode_list()

    def render_episode_list(self) -> None:
        lv = self.query_one("#episodes", ListView)
        lv.clear()
        self.episode_numbers = sorted(self.episode_map.keys())
        for ep in self.episode_numbers:
            lv.append(ListItem(Static(f"Episode {ep}")))
        if self.selected_episode in self.episode_numbers:
            lv.index = self.episode_numbers.index(self.selected_episode)

    def render_info(self, t: Title) -> None:
        available_count = len(self.episode_map)
        selected_ep = str(self.selected_episode) if self.selected_episode is not None else "-"
        info = (
            f"[b]{t.name_ru or '-'}[/b]\n"
            f"{t.name_en or ''}\n\n"
            f"Year: {t.year or '-'}\n"
            f"Episode: {selected_ep}\n"
            f"Episodes: {available_count}\n"
            f"Quality: {self.quality}\n"
            f"Status: {self.status_message}\n\n"
            f"{(t.description or '').strip()[:800]}"
        )
        self.query_one("#info", Static).update(info)

    def action_cycle_quality(self) -> None:
        i = QUALITY_ORDER.index(self.quality) if self.quality in QUALITY_ORDER else 0
        self.quality = QUALITY_ORDER[(i + 1) % len(QUALITY_ORDER)]
        if self.selected:
            self.status_message = f"Quality: {self.quality}"
            self.render_info(self.selected)

    def action_prev_episode(self) -> None:
        if not self.selected:
            return
        if not self.episode_map:
            self.load_episodes_for_selected()
        if not self.episode_map:
            return
        eps = sorted(self.episode_map.keys())
        if self.selected_episode is None or self.selected_episode not in self.episode_map:
            self.selected_episode = eps[0]
        else:
            i = eps.index(self.selected_episode)
            self.selected_episode = eps[max(0, i - 1)]
        self.render_episode_list()
        self.render_info(self.selected)

    def action_next_episode(self) -> None:
        if not self.selected:
            return
        if not self.episode_map:
            self.load_episodes_for_selected()
        if not self.episode_map:
            return
        eps = sorted(self.episode_map.keys())
        if self.selected_episode is None or self.selected_episode not in self.episode_map:
            self.selected_episode = eps[0]
        else:
            i = eps.index(self.selected_episode)
            self.selected_episode = eps[min(len(eps) - 1, i + 1)]
        self.render_episode_list()
        self.render_info(self.selected)

    def action_play(self) -> None:
        if not self.selected:
            return
        try:
            if not self.episode_map:
                self.load_episodes_for_selected()
            if not self.episode_map:
                self.status_message = "No episodes in this release"
                self.render_info(self.selected)
                return

            if self.selected_episode not in self.episode_map:
                self.selected_episode = sorted(self.episode_map.keys())[0]
            episode = self.episode_map[self.selected_episode]
            stream_url, actual_quality = pick_episode_stream_url(episode, self.quality)
            if not stream_url:
                self.status_message = "No stream URL for selected quality"
                self.render_info(self.selected)
                return

            used_player = play_url(stream_url)
            ep_num = self.selected_episode if self.selected_episode is not None else "?"
            if actual_quality and actual_quality != self.quality and self.quality not in ("best", "worst"):
                self.status_message = (
                    f"Playing ep {ep_num} via {used_player} ({self.quality} -> {actual_quality})"
                )
            else:
                self.status_message = f"Playing ep {ep_num} via {used_player} ({actual_quality or self.quality})"
            self.render_info(self.selected)
        except Exception as e:
            self.status_message = f"Playback error: {e}"
            self.render_info(self.selected)

    def action_download(self) -> None:
        if not self.selected:
            return
        try:
            if not self.episode_map:
                self.load_episodes_for_selected()
            if not self.episode_map:
                self.status_message = "No episodes in this release"
                self.render_info(self.selected)
                return

            if self.selected_episode not in self.episode_map:
                self.selected_episode = sorted(self.episode_map.keys())[0]
            episode = self.episode_map[self.selected_episode]
            stream_url, actual_quality = pick_episode_stream_url(episode, self.quality)
            if not stream_url:
                self.status_message = "No stream URL for selected quality"
                self.render_info(self.selected)
                return

            title_name = self.selected.name_ru or self.selected.name_en or self.selected.id
            ep_num = self.selected_episode if self.selected_episode is not None else 0
            q_for_name = actual_quality or self.quality
            mode, saved_path = download_episode_stream(stream_url, title_name, ep_num, q_for_name)
            if actual_quality and actual_quality != self.quality and self.quality not in ("best", "worst"):
                self.status_message = f"Downloaded ({mode}) [{self.quality}->{actual_quality}]"
            else:
                self.status_message = f"Downloaded ({mode}) [{q_for_name}]"
            self.render_info(self.selected)
        except Exception as e:
            self.status_message = f"Download error: {e}"
            self.render_info(self.selected)


def main() -> None:
    AniCliRuTUI().run()


if __name__ == "__main__":
    main()
