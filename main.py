import base64
import json
import re
import shutil
import subprocess
import threading
import tkinter as tk
from html import unescape
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests


class AniLibriaClient:
    BASE_URL = "https://api.anilibria.app/api/v1"

    # Доступные языки озвучки
    DUB_LANGUAGES = [
        {"code": "ru", "name": "Русский (AniLibria)", "type": "dub"},
        {"code": "en", "name": "English (AniQit)", "type": "dub"},
        {"code": "uk", "name": "Українська (AniQit)", "type": "dub"},
        {"code": "tr", "name": "Türkçe (AniQit)", "type": "dub"},
        {"code": "sub_ru", "name": "Русские субтитры", "type": "sub"},
        {"code": "sub_en", "name": "English subtitles", "type": "sub"},
    ]

    def __init__(self, language="ru", dubbing="ru", timeout=20):
        self.language = language
        self.dubbing = dubbing
        self.timeout = timeout

    def _get(self, path, params=None):
        response = requests.get(
            f"{self.BASE_URL}/{path.lstrip('/')}",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def search(self, query, limit=30, page=1):
        return self._get(
            "app/search/releases",
            {
                "query": query,
                "limit": limit,
                "page": page,
                "filter": "id,type,year,name,description,episodes_total,latest_episode",
            },
        )

    def latest(self, limit=15):
        data = self._get("anime/releases/latest", {"limit": limit})
        return data if isinstance(data, list) else [data]

    def random(self, limit=10):
        data = self._get("anime/releases/random", {"limit": limit})
        return data if isinstance(data, list) else [data]

    def by_id(self, release_id):
        return self._get(
            f"anime/releases/{release_id}",
            {"filter": "id,type,year,name,description,episodes_total,latest_episode,genres,episodes,external_player"},
        )


class HistoryStore:
    def __init__(self, max_items=50):
        self.max_items = max_items
        self.path = Path.home() / ".ani_cli_ru_gui_history.json"

    def _load(self):
        if not self.path.exists():
            return []
        try:
            content = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        ids = content.get("release_ids", [])
        return [int(item) for item in ids if str(item).isdigit()]

    def _save(self, release_ids):
        payload = {"release_ids": release_ids[: self.max_items]}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, release_id):
        if release_id is None:
            return
        rid = int(release_id)
        current = self._load()
        if rid in current:
            current.remove(rid)
        current.insert(0, rid)
        self._save(current)

    def get_ids(self):
        return self._load()


class AniCliRuGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.client = AniLibriaClient(language="ru", dubbing="ru")
        self.history = HistoryStore()
        self.release_map = {}
        self.menu_widgets = []

        self.title("ani-cli-ru GUI - Multi-Language")
        self.geometry("1200x700")
        self.minsize(900, 560)

        self.query_var = tk.StringVar()
        self.lang_var = tk.StringVar(value="ru")
        self.dubbing_var = tk.StringVar(value="ru")
        self.status_var = tk.StringVar(value="Ready")
        self.dark_mode_var = tk.BooleanVar(value=False)
        self.selected_episode_var = tk.StringVar()
        self.watch_mode_var = tk.StringVar(value="RU HLS (AniLibria)")
        self.resolution_var = tk.StringVar(value="1080")
        self.style = ttk.Style(self)

        self._build_menu()
        self._build_layout()
        self._apply_theme()

    def _build_menu(self):
        menu = tk.Menu(self)
        rec_menu = tk.Menu(menu, tearoff=False)
        rec_menu.add_command(label="Smart Recommendations", command=self.load_smart_recommendations)
        rec_menu.add_command(label="Latest Releases", command=self.load_latest_recommendations)
        rec_menu.add_command(label="Random Picks", command=self.load_random_recommendations)
        menu.add_cascade(label="Recommendations", menu=rec_menu)
        
        # Меню выбора озвучки
        dub_menu = tk.Menu(menu, tearoff=False)
        self.dub_vars = {}
        for dub in AniLibriaClient.DUB_LANGUAGES:
            var = tk.StringVar(value="")
            self.dub_vars[dub["code"]] = var
            dub_menu.add_radiobutton(
                label=dub["name"],
                variable=var,
                value=dub["code"],
                command=lambda d=dub["code"]: self._apply_dubbing(d)
            )
        menu.add_cascade(label="Dubbing / Озвучка", menu=dub_menu)
        
        view_menu = tk.Menu(menu, tearoff=False)
        view_menu.add_checkbutton(label="Dark Mode", variable=self.dark_mode_var, command=self.toggle_dark_mode)
        menu.add_cascade(label="View", menu=view_menu)
        self.menu_widgets = [menu, rec_menu, dub_menu, view_menu]
        self.config(menu=menu)

    def _build_layout(self):
        top = ttk.Frame(self, padding=(10, 10, 10, 4))
        top.pack(fill=tk.X)

        ttk.Label(top, text="Search").pack(side=tk.LEFT)
        entry = ttk.Entry(top, textvariable=self.query_var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        entry.bind("<Return>", lambda _: self.search())

        ttk.Label(top, text="Lang").pack(side=tk.LEFT, padx=(8, 4))
        lang = ttk.Combobox(
            top,
            textvariable=self.lang_var,
            values=["ru", "en"],
            state="readonly",
            width=5,
        )
        lang.pack(side=tk.LEFT)
        lang.bind("<<ComboboxSelected>>", lambda _: self._apply_language())

        ttk.Label(top, text="Dub").pack(side=tk.LEFT, padx=(12, 4))
        dub_values = [d["name"] for d in AniLibriaClient.DUB_LANGUAGES]
        self.dub_combo = ttk.Combobox(
            top,
            textvariable=self.dubbing_var,
            values=dub_values,
            state="readonly",
            width=22,
        )
        self.dub_combo.pack(side=tk.LEFT)
        self.dub_combo.bind("<<ComboboxSelected>>", lambda _: self._apply_dubbing_from_combo())

        ttk.Button(top, text="Search", command=self.search).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(top, text="Smart Recs", command=self.load_smart_recommendations).pack(side=tk.LEFT, padx=(6, 0))

        body = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        left = ttk.Frame(body, padding=4)
        right = ttk.Frame(body, padding=4)
        body.add(left, weight=3)
        body.add(right, weight=2)

        columns = ("title", "type", "year", "episodes", "reason")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", height=18)
        self.tree.heading("title", text="Title")
        self.tree.heading("type", text="Type")
        self.tree.heading("year", text="Year")
        self.tree.heading("episodes", text="Eps")
        self.tree.heading("reason", text="Reason")
        self.tree.column("title", width=370, anchor=tk.W)
        self.tree.column("type", width=70, anchor=tk.CENTER)
        self.tree.column("year", width=70, anchor=tk.CENTER)
        self.tree.column("episodes", width=70, anchor=tk.CENTER)
        self.tree.column("reason", width=150, anchor=tk.W)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_release)

        tree_scroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        episode_bar = ttk.Frame(right)
        episode_bar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(episode_bar, text="Episode").pack(side=tk.LEFT)
        self.episode_combo = ttk.Combobox(
            episode_bar,
            textvariable=self.selected_episode_var,
            state="disabled",
            width=10,
        )
        self.episode_combo.pack(side=tk.LEFT, padx=(8, 6))
        self.episode_combo.bind("<<ComboboxSelected>>", self.select_episode)
        self.episode_combo.bind("<Return>", self.select_episode)
        self.episode_btn = ttk.Button(episode_bar, text="Select", command=self.select_episode, state=tk.DISABLED)
        self.episode_btn.pack(side=tk.LEFT)

        watch_bar = ttk.Frame(right)
        watch_bar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(watch_bar, text="Watch").pack(side=tk.LEFT)
        self.watch_mode_combo = ttk.Combobox(
            watch_bar,
            textvariable=self.watch_mode_var,
            state="readonly",
            width=22,
            values=["RU HLS (AniLibria)", "JP/Subs (External)"],
        )
        self.watch_mode_combo.pack(side=tk.LEFT, padx=(8, 6))
        self.watch_open_btn = ttk.Button(watch_bar, text="Open", command=self.open_selected_episode)
        self.watch_open_btn.pack(side=tk.LEFT)

        res_bar = ttk.Frame(right)
        res_bar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(res_bar, text="Resolution").pack(side=tk.LEFT)
        self.resolution_combo = ttk.Combobox(
            res_bar,
            textvariable=self.resolution_var,
            state="readonly",
            width=10,
            values=["4K", "2K", "1080", "720", "480", "360"],
        )
        self.resolution_combo.pack(side=tk.LEFT, padx=(8, 6))
        
        # Обновляем watch mode при изменении озвучки
        self.dubbing_var.trace_add("write", lambda *args: self._update_watch_mode_options())

        self.detail_text = tk.Text(right, wrap=tk.WORD, state=tk.DISABLED)
        self.detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.detail_text.yview)
        detail_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.detail_text.configure(yscrollcommand=detail_scroll.set)

        status = ttk.Label(self, textvariable=self.status_var, anchor=tk.W, padding=(10, 4))
        status.pack(fill=tk.X)

    def _apply_language(self):
        self.client.language = self.lang_var.get().strip().lower() or "ru"

    def _apply_dubbing(self, dub_code):
        """Применить выбранную озвучку по коду"""
        self.client.dubbing = dub_code
        self.dubbing_var.set(dub_code)
        self._update_watch_mode_options()
        self._set_status(f"Selected dubbing: {dub_code}")

    def _apply_dubbing_from_combo(self):
        """Применить выбранную озвучку из комбобокса"""
        selected_name = self.dubbing_var.get()
        for dub in AniLibriaClient.DUB_LANGUAGES:
            if dub["name"] == selected_name:
                self.client.dubbing = dub["code"]
                # Обновляем меню
                for code, var in self.dub_vars.items():
                    var.set(dub["code"] if code == dub["code"] else "")
                self._update_watch_mode_options()
                self._set_status(f"Selected dubbing: {dub['name']}")
                break

    def _update_watch_mode_options(self):
        """Обновить опции режима просмотра на основе выбранной озвучки"""
        dub_type = None
        for dub in AniLibriaClient.DUB_LANGUAGES:
            if dub["code"] == self.client.dubbing:
                dub_type = dub["type"]
                break
        
        if dub_type == "sub" or self.client.dubbing in ["en", "uk", "tr"]:
            # Для субтитров и иностранных озвучек используем внешний плеер
            self.watch_mode_combo.configure(values=["JP/Subs (External)"], state="readonly")
            self.watch_mode_var.set("JP/Subs (External)")
        else:
            # Для русской озвучки доступны оба режима
            self.watch_mode_combo.configure(values=["RU HLS (AniLibria)", "JP/Subs (External)"], state="readonly")
            self.watch_mode_var.set("RU HLS (AniLibria)")

    def toggle_dark_mode(self):
        self._apply_theme()

    def _apply_theme(self):
        dark = self.dark_mode_var.get()
        palette = {
            "bg": "#1E1E1E" if dark else "#F2F2F2",
            "panel": "#252526" if dark else "#FFFFFF",
            "field": "#2D2D30" if dark else "#FFFFFF",
            "fg": "#EAEAEA" if dark else "#111111",
            "muted": "#CFCFCF" if dark else "#333333",
            "accent": "#0E639C" if dark else "#1A73E8",
            "select_fg": "#FFFFFF",
            "border": "#3C3C3C" if dark else "#C9C9C9",
        }

        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.configure(bg=palette["bg"])
        self.style.configure(".", background=palette["bg"], foreground=palette["fg"])
        self.style.configure("TFrame", background=palette["bg"])
        self.style.configure("TPanedwindow", background=palette["bg"])
        self.style.configure("TLabel", background=palette["bg"], foreground=palette["fg"])
        self.style.configure(
            "TButton",
            background=palette["panel"],
            foreground=palette["fg"],
            bordercolor=palette["border"],
            focuscolor=palette["accent"],
            padding=4,
        )
        self.style.map(
            "TButton",
            background=[("active", palette["accent"])],
            foreground=[("active", palette["select_fg"])],
        )
        self.style.configure(
            "TEntry",
            fieldbackground=palette["field"],
            foreground=palette["fg"],
            bordercolor=palette["border"],
            insertcolor=palette["fg"],
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=palette["field"],
            background=palette["field"],
            foreground=palette["fg"],
            bordercolor=palette["border"],
            arrowcolor=palette["fg"],
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", palette["field"])],
            foreground=[("readonly", palette["fg"])],
            selectbackground=[("readonly", palette["accent"])],
            selectforeground=[("readonly", palette["select_fg"])],
        )
        self.style.configure(
            "Treeview",
            background=palette["panel"],
            fieldbackground=palette["panel"],
            foreground=palette["fg"],
            bordercolor=palette["border"],
            rowheight=22,
        )
        self.style.map(
            "Treeview",
            background=[("selected", palette["accent"])],
            foreground=[("selected", palette["select_fg"])],
        )
        self.style.configure(
            "Treeview.Heading",
            background=palette["bg"],
            foreground=palette["fg"],
            bordercolor=palette["border"],
        )
        self.style.map("Treeview.Heading", background=[("active", palette["panel"])])
        self.style.configure("Vertical.TScrollbar", background=palette["panel"], troughcolor=palette["bg"])

        self.option_add("*TCombobox*Listbox.background", palette["field"])
        self.option_add("*TCombobox*Listbox.foreground", palette["fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", palette["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", palette["select_fg"])

        self.detail_text.configure(
            bg=palette["panel"],
            fg=palette["fg"],
            insertbackground=palette["fg"],
            selectbackground=palette["accent"],
            selectforeground=palette["select_fg"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=palette["border"],
            highlightcolor=palette["accent"],
        )

        for menu in self.menu_widgets:
            menu.configure(
                bg=palette["panel"],
                fg=palette["fg"],
                activebackground=palette["accent"],
                activeforeground=palette["select_fg"],
                relief=tk.FLAT,
                borderwidth=1,
            )

    def _set_status(self, text):
        self.status_var.set(text)

    def _clear_episode_selector(self):
        self.selected_episode_var.set("")
        self.episode_combo.configure(values=(), state="disabled")
        self.episode_btn.configure(state=tk.DISABLED)

    def _episode_limit(self, release):
        available = release.get("available_episode_numbers") or []
        if available:
            return max(available)
        total = release.get("episodes_total_value")
        latest = release.get("latest_episode_value")
        if isinstance(latest, int) and latest > 0:
            return latest
        if isinstance(total, int) and total > 0:
            return total
        return None

    def _populate_episode_selector(self, release):
        available = release.get("available_episode_numbers") or []
        if available:
            values = [str(i) for i in available]
            default_episode = available[-1]
        else:
            limit = self._episode_limit(release)
            if not limit:
                self._clear_episode_selector()
                return
            values = [str(i) for i in range(1, limit + 1)]
            default_episode = release.get("latest_episode_value") or 1

        self.episode_combo.configure(values=values, state="readonly")
        self.episode_btn.configure(state=tk.NORMAL)

        selected = release.get("selected_episode")
        if available:
            if not isinstance(selected, int) or selected not in available:
                selected = default_episode
        else:
            limit = self._episode_limit(release)
            if not isinstance(selected, int) or selected < 1 or selected > limit:
                selected = default_episode

        release["selected_episode"] = int(selected)
        self.selected_episode_var.set(str(release["selected_episode"]))

    def select_episode(self, _event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        rid = selected_items[0]
        release = self.release_map.get(rid)
        if not release:
            return

        raw = self.selected_episode_var.get().strip()
        if not raw:
            return
        if not raw.isdigit():
            messagebox.showinfo("ani-cli-ru GUI", "Episode number must be numeric.")
            return

        episode = int(raw)
        available = release.get("available_episode_numbers") or []
        if available:
            if episode not in set(available):
                messagebox.showinfo("ani-cli-ru GUI", "This episode is not available in the current list.")
                return
        else:
            limit = self._episode_limit(release)
            if limit and not (1 <= episode <= limit):
                messagebox.showinfo("ani-cli-ru GUI", f"Episode must be between 1 and {limit}.")
                return

        release["selected_episode"] = episode
        self._set_detail_text(self._format_detail(release))
        self._set_status(f"Selected episode {episode}: {release['title']}")

    def _current_release(self):
        selected_items = self.tree.selection()
        if not selected_items:
            return None
        return self.release_map.get(selected_items[0])

    def open_selected_episode(self):
        release = self._current_release()
        if not release:
            messagebox.showinfo("ani-cli-ru GUI", "Select an anime first.")
            return

        if not release.get("details_loaded"):
            messagebox.showinfo(
                "ani-cli-ru GUI",
                "Details are still loading. Please wait a moment and try again.",
            )
            return

        mode = self.watch_mode_var.get().strip()
        if mode == "JP/Subs (External)":
            self._open_external_player(release)
            return

        self._open_anilibria_hls(release)

    def _open_anilibria_hls(self, release):
        selected = release.get("selected_episode")
        if not isinstance(selected, int):
            messagebox.showinfo("ani-cli-ru GUI", "Select an episode first.")
            return

        episode_streams = release.get("episode_streams") or {}
        streams = episode_streams.get(selected)
        if not isinstance(streams, dict):
            messagebox.showinfo(
                "ani-cli-ru GUI",
                "This episode stream is not available in AniLibria data.",
            )
            return

        # Маппинг выбранных разрешений на ключи в streams
        resolution_map = {
            "4K": ["hls_2160", "hls_4k", "hls_1080"],
            "2K": ["hls_1440", "hls_2k", "hls_1080"],
            "1080": ["hls_1080", "hls_720"],
            "720": ["hls_720", "hls_480"],
            "480": ["hls_480", "hls_360"],
            "360": ["hls_360", "hls_480"],
        }

        selected_res = self.resolution_var.get()
        quality_keys = resolution_map.get(selected_res, ["hls_1080", "hls_720", "hls_480"])

        url = None
        for key in quality_keys:
            url = streams.get(key)
            if url:
                break

        if not url:
            # Если ни одно качество не найдено, пробуем все доступные
            for key in ["hls_1080", "hls_720", "hls_480", "hls_360"]:
                url = streams.get(key)
                if url:
                    break

        if not url:
            messagebox.showinfo(
                "ani-cli-ru GUI",
                "No playable HLS URL was found for this episode.",
            )
            return

        try:
            player_name = self._launch_player(url, title=release["title"])
        except RuntimeError as exc:
            messagebox.showerror("ani-cli-ru GUI", str(exc))
            self._set_status(str(exc))
            return

        self._set_status(f"Opened RU HLS ({selected_res}) in {player_name} for episode {selected}: {release['title']}")

    def _open_external_player(self, release):
        url = release.get("external_player_url") or release.get("manual_external_player_url")
        if not url:
            url = self._prompt_kodik_player_url(release)
            if not url:
                return
            release["manual_external_player_url"] = url

        selected_episode = release.get("selected_episode")
        if not isinstance(selected_episode, int):
            messagebox.showinfo("ani-cli-ru GUI", "Select an episode first.")
            return

        title = release["title"]
        dubbing = self.client.dubbing
        
        # Определяем тип озвучки для выбора перевода
        if dubbing == "ru":
            # Русская озвучка - используем стандартный поток AniLibria
            self._open_anilibria_hls(release)
            return
        elif dubbing in ["en", "uk", "tr"]:
            # Иностранная озвучка - ищем соответствующий перевод
            self._run_async(
                worker=lambda: self._resolve_kodik_dub_stream(url, selected_episode, dubbing),
                on_success=lambda result: self._open_resolved_external_stream(result, title, selected_episode),
                loading_text=f"Resolving {dubbing} dubbing: {title}",
            )
        elif dubbing.startswith("sub_"):
            # Субтитры
            self._run_async(
                worker=lambda: self._resolve_kodik_subs_stream(self._with_translations_enabled(url), selected_episode),
                on_success=lambda result: self._open_resolved_external_stream(result, title, selected_episode),
                loading_text=f"Resolving subtitles ({dubbing}): {title}",
            )
        else:
            # По умолчанию - субтитры
            self._run_async(
                worker=lambda: self._resolve_kodik_subs_stream(self._with_translations_enabled(url), selected_episode),
                on_success=lambda result: self._open_resolved_external_stream(result, title, selected_episode),
                loading_text=f"Resolving JP/Subs source: {title}",
            )

    def _prompt_kodik_player_url(self, release):
        title = release.get("title") or "anime"
        text = simpledialog.askstring(
            "JP/Subs Source",
            (
                "Auto JP/Subs source was not found.\n"
                "Paste a Kodik player URL for this title (serial/.../720p).\n\n"
                f"Title: {title}"
            ),
            parent=self,
        )
        if text is None:
            return None

        url = self._normalize_external_player_url(text)
        if not url:
            messagebox.showinfo("ani-cli-ru GUI", "Invalid URL.")
            return None

        if not url.startswith(("http://", "https://")):
            messagebox.showinfo("ani-cli-ru GUI", "Please enter a full URL starting with http:// or https://")
            return None

        return url

    def _open_resolved_external_stream(self, result, title, episode_number):
        stream_url = result.get("stream_url")
        referer = result.get("referer")
        translation_title = result.get("translation_title") or "subtitles"
        if not stream_url:
            messagebox.showerror("ani-cli-ru GUI", "Failed to resolve JP/Subs stream URL.")
            self._set_status("Failed to resolve JP/Subs stream URL")
            return

        try:
            player_name = self._launch_player(stream_url, title=title, referer=referer)
        except RuntimeError as exc:
            messagebox.showerror("ani-cli-ru GUI", str(exc))
            self._set_status(str(exc))
            return

        self._set_status(
            f"Opened JP/Subs ({translation_title}) in {player_name} for episode {episode_number}: {title}",
        )

    def _launch_player(self, url, title, referer=None):
        player = self._find_player_command()
        if not player:
            raise RuntimeError("No supported local player found. Install mpv or VLC and try again.")

        name = player["name"]
        exe = player["path"]
        if name == "mpv":
            cmd = [
                exe,
                "--force-window=yes",
                f"--force-media-title={title}",
                "--keepaspect=yes",
                "--panscan=0",
                "--cache=yes",
                "--cache-secs=10",
                "--demuxer-max-bytes=128MiB",
                "--hls-bitrate=9999999",
                "--hr-seek=yes",
                "--hwdec=no",
                "--prefetch-playlist=yes",
            ]
            if referer:
                cmd.append(f"--http-header-fields=Referer: {referer}")
            cmd.append(url)
        elif name == "vlc":
            cmd = [exe, url]
            if referer:
                cmd.insert(1, f":http-referrer={referer}")
        else:
            cmd = [exe, url]

        try:
            subprocess.Popen(cmd)
        except OSError as exc:
            raise RuntimeError(f"Failed to start player ({name}): {exc}") from exc
        return name

    @staticmethod
    def _find_player_command():
        # Проверяем PATH
        for name in ("mpv", "vlc", "ffplay"):
            path = shutil.which(name)
            if path:
                return {"name": name, "path": path}
        
        # Проверяем стандартные пути установки VLC на Windows
        vlc_paths = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            str(Path.home() / "AppData/Local/Programs/VLC/vlc.exe"),
        ]
        for vlc_path in vlc_paths:
            if Path(vlc_path).exists():
                return {"name": "vlc", "path": vlc_path}
        
        return None

    def _resolve_kodik_subs_stream(self, external_player_url, episode_number):
        page = self._fetch_kodik_page(external_player_url)
        translations = page.get("translations") or []
        subtitles_translation = self._pick_kodik_subtitles_translation(translations)
        if not subtitles_translation:
            raise RuntimeError("Kodik subtitles translation was not found for this title.")

        subs_page_url = self._build_kodik_media_url(
            media_type=subtitles_translation["media_type"],
            media_id=subtitles_translation["media_id"],
            media_hash=subtitles_translation["media_hash"],
            source_url=external_player_url,
        )
        subs_page = self._fetch_kodik_page(subs_page_url)
        episode_map = subs_page.get("episodes") or {}
        episode = episode_map.get(int(episode_number))
        if not episode:
            raise RuntimeError(f"Subtitles translation does not have episode {episode_number}.")

        ftor_data = self._kodik_ftor(
            page_url=subs_page["page_url"],
            url_params=subs_page["url_params"],
            episode_id=episode["id"],
            episode_hash=episode["hash"],
        )
        stream_url = self._pick_kodik_stream_url(ftor_data)
        if not stream_url:
            raise RuntimeError("Could not decode a playable Kodik stream URL.")

        return {
            "stream_url": stream_url,
            "referer": subs_page["page_url"],
            "translation_title": subtitles_translation.get("title") or "Subtitles",
        }

    def _fetch_kodik_page(self, page_url):
        response = requests.get(
            page_url,
            timeout=25,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()
        html = response.text

        url_params_match = re.search(r"var urlParams = '([^']+)';", html)
        if not url_params_match:
            raise RuntimeError("Failed to parse Kodik page (urlParams missing).")

        try:
            url_params = json.loads(url_params_match.group(1))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Failed to parse Kodik page params.") from exc

        return {
            "page_url": response.url,
            "html": html,
            "url_params": url_params,
            "episodes": self._parse_kodik_episode_options(html),
            "translations": self._parse_kodik_translation_options(html),
        }

    def _kodik_ftor(self, page_url, url_params, episode_id, episode_hash):
        payload = {key: url_params.get(key, "") for key in ("d", "d_sign", "pd", "pd_sign", "ref", "ref_sign")}
        payload.update(
            {
                "bad_user": "false",
                "cdn_is_working": "true",
                "type": "seria",
                "id": str(episode_id),
                "hash": str(episode_hash),
            }
        )
        response = requests.post(
            "https://kodik.info/ftor",
            data=payload,
            timeout=25,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": page_url,
                "Origin": "https://kodik.info",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        response.raise_for_status()
        return response.json()

    def _pick_kodik_stream_url(self, ftor_data):
        links = ftor_data.get("links")
        if not isinstance(links, dict):
            return None

        qualities = []
        for quality, variants in links.items():
            try:
                q_num = int(quality)
            except (TypeError, ValueError):
                continue
            if isinstance(variants, list) and variants:
                qualities.append((q_num, variants))

        for _q, variants in sorted(qualities, key=lambda item: item[0], reverse=True):
            for variant in variants:
                if not isinstance(variant, dict):
                    continue
                encoded = variant.get("src")
                if not isinstance(encoded, str) or not encoded.strip():
                    continue
                decoded = self._decode_kodik_stream_src(encoded.strip())
                if decoded:
                    return decoded
        return None

    @staticmethod
    def _decode_kodik_stream_src(encoded_value):
        try:
            shifted = "".join(AniCliRuGui._shift_kodik_alpha(char) for char in encoded_value)
            decoded = base64.b64decode(shifted).decode("utf-8")
        except Exception:  # noqa: BLE001
            return None

        decoded = decoded.strip()
        if decoded.startswith("//"):
            return f"https:{decoded}"
        return decoded or None

    @staticmethod
    def _shift_kodik_alpha(char):
        if "a" <= char <= "z":
            return chr(ord("a") + ((ord(char) - ord("a") + 18) % 26))
        if "A" <= char <= "Z":
            return chr(ord("A") + ((ord(char) - ord("A") + 18) % 26))
        return char

    def _parse_kodik_episode_options(self, html):
        options = self._parse_kodik_select_options(html, "serial-series-box")
        episode_map = {}
        for option in options:
            number = self._safe_int(option.get("value"))
            if number is None or number <= 0:
                continue
            episode_id = option.get("data-id")
            episode_hash = option.get("data-hash")
            if not episode_id or not episode_hash:
                continue
            episode_map[number] = {"id": episode_id, "hash": episode_hash}
        return episode_map

    def _parse_kodik_translation_options(self, html):
        options = self._parse_kodik_select_options(html, "serial-translations-box")
        translations = []
        for option in options:
            media_id = option.get("data-media-id")
            media_hash = option.get("data-media-hash")
            media_type = option.get("data-media-type")
            if not media_id or not media_hash or not media_type:
                continue
            translations.append(
                {
                    "id": option.get("data-id") or option.get("value"),
                    "translation_type": (option.get("data-translation-type") or "").strip().lower(),
                    "media_id": str(media_id),
                    "media_hash": str(media_hash),
                    "media_type": str(media_type),
                    "title": (option.get("data-title") or option.get("_text") or "").strip(),
                }
            )
        return translations

    @staticmethod
    def _pick_kodik_subtitles_translation(translations):
        for item in translations:
            if item.get("translation_type") == "subtitles":
                return item
        for item in translations:
            title = (item.get("title") or "").lower()
            if "субт" in title or "sub" in title:
                return item
        return None

    def _resolve_kodik_dub_stream(self, external_player_url, episode_number, dubbing_code):
        """Разрешить поток для иностранной озвучки (en, uk, tr)"""
        page = self._fetch_kodik_page(external_player_url)
        translations = page.get("translations") or []
        
        # Выбираем озвучку по коду языка
        dub_translation = self._pick_kodik_dub_translation(translations, dubbing_code)
        if not dub_translation:
            raise RuntimeError(f"Kodik {dubbing_code} dubbing was not found for this title.")

        dub_page_url = self._build_kodik_media_url(
            media_type=dub_translation["media_type"],
            media_id=dub_translation["media_id"],
            media_hash=dub_translation["media_hash"],
            source_url=external_player_url,
        )
        dub_page = self._fetch_kodik_page(dub_page_url)
        episode_map = dub_page.get("episodes") or {}
        episode = episode_map.get(int(episode_number))
        if not episode:
            raise RuntimeError(f"Dubbing does not have episode {episode_number}.")

        ftor_data = self._kodik_ftor(
            page_url=dub_page["page_url"],
            url_params=dub_page["url_params"],
            episode_id=episode["id"],
            episode_hash=episode["hash"],
        )
        stream_url = self._pick_kodik_stream_url(ftor_data)
        if not stream_url:
            raise RuntimeError("Could not decode a playable Kodik stream URL.")

        return {
            "stream_url": stream_url,
            "referer": dub_page["page_url"],
            "translation_title": dub_translation.get("title") or f"{dubbing_code} dubbing",
        }

    @staticmethod
    def _pick_kodik_dub_translation(translations, dubbing_code):
        """Выбрать озвучку по коду языка"""
        # Маппинг кодов языков на ключевые слова для поиска
        lang_keywords = {
            "en": ["english", "eng", "английский", "en "],
            "uk": ["ukrainian", "ukr", "український", "украинский", "uk "],
            "tr": ["turkish", "türkçe", "turk", "tr "],
        }
        
        keywords = lang_keywords.get(dubbing_code, [])
        
        # Сначала ищем по translation_type
        for item in translations:
            trans_type = item.get("translation_type", "").lower()
            if trans_type == "voice" or trans_type == "dubbing":
                title = (item.get("title") or "").lower()
                for keyword in keywords:
                    if keyword in title:
                        return item
        
        # Затем ищем по названию
        for item in translations:
            title = (item.get("title") or "").lower()
            for keyword in keywords:
                if keyword in title:
                    return item
        
        return None

    @staticmethod
    def _parse_kodik_select_options(html, box_class):
        match = re.search(
            rf'<div class="{re.escape(box_class)}"[^>]*>.*?<select>(.*?)</select>',
            html,
            flags=re.S,
        )
        if not match:
            return []

        options_html = match.group(1)
        results = []
        for attrs_raw, label_raw in re.findall(r"<option\b([^>]*)>(.*?)</option>", options_html, flags=re.S):
            attrs = AniCliRuGui._parse_html_attributes(attrs_raw)
            label = re.sub(r"\s+", " ", re.sub(r"<.*?>", "", label_raw)).strip()
            attrs["_text"] = unescape(label)
            results.append(attrs)
        return results

    @staticmethod
    def _parse_html_attributes(attrs_raw):
        attrs = {}
        for key, value in re.findall(r'([:\w-]+)\s*=\s*"([^"]*)"', attrs_raw):
            attrs[key] = unescape(value)
        return attrs

    @staticmethod
    def _build_kodik_media_url(media_type, media_id, media_hash, source_url):
        source_parts = urlsplit(source_url)
        query = dict(parse_qsl(source_parts.query, keep_blank_values=True))
        query["translations"] = "true"
        path = f"/{media_type}/{media_id}/{media_hash}/720p"
        return urlunsplit((source_parts.scheme or "https", source_parts.netloc or "kodik.info", path, urlencode(query), ""))

    @staticmethod
    def _with_translations_enabled(url):
        try:
            parts = urlsplit(url)
            query = dict(parse_qsl(parts.query, keep_blank_values=True))
            query["translations"] = "true"
            return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
        except Exception:  # noqa: BLE001
            return url.replace("translations=false", "translations=true")

    def _load_release_details(self, release_id, reason):
        release = self.client.by_id(release_id)
        release["_reason"] = reason
        return release

    def _apply_release_details(self, tree_iid, raw_release):
        current = self.release_map.get(tree_iid)
        if not current:
            return

        previous_selected = current.get("selected_episode")
        previous_manual_external = current.get("manual_external_player_url")
        normalized = self._normalize_release(raw_release)
        normalized["selected_episode"] = previous_selected
        normalized["manual_external_player_url"] = previous_manual_external
        self.release_map[tree_iid] = normalized

        self.tree.item(
            tree_iid,
            values=(
                normalized["title"],
                normalized["type"],
                normalized["year"],
                normalized["episodes"],
                normalized["reason"],
            ),
        )

        selected = self.tree.selection()
        if selected and selected[0] == tree_iid:
            self._populate_episode_selector(normalized)
            self._set_detail_text(self._format_detail(normalized))
            self._set_status(f"Loaded details: {normalized['title']}")

    def _run_async(self, worker, on_success, loading_text):
        self._set_status(loading_text)

        def run():
            try:
                result = worker()
            except requests.RequestException as exc:
                self.after(0, lambda: self._show_error(f"API error: {exc}"))
                return
            except RuntimeError as exc:
                self.after(0, lambda: self._show_error(str(exc)))
                return
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._show_error(f"Unexpected error: {exc}"))
                return
            self.after(0, lambda: on_success(result))

        threading.Thread(target=run, daemon=True).start()

    def _show_error(self, message):
        self._set_status(message)
        messagebox.showerror("ani-cli-ru GUI", message)

    def search(self):
        query = self.query_var.get().strip()
        if not query:
            messagebox.showinfo("ani-cli-ru GUI", "Enter a search query first.")
            return
        self._apply_language()
        self._run_async(
            worker=lambda: self.client.search(query=query, limit=40, page=1),
            on_success=lambda rows: self._render_results(rows, "Search complete"),
            loading_text=f"Searching: {query}",
        )

    def load_latest_recommendations(self):
        self._apply_language()
        self._run_async(
            worker=lambda: self._annotate_reason(self.client.latest(limit=18), "Fresh release"),
            on_success=lambda rows: self._render_results(rows, "Latest recommendations loaded"),
            loading_text="Loading latest recommendations",
        )

    def load_random_recommendations(self):
        self._apply_language()
        self._run_async(
            worker=lambda: self._annotate_reason(self.client.random(limit=18), "Random pick"),
            on_success=lambda rows: self._render_results(rows, "Random recommendations loaded"),
            loading_text="Loading random recommendations",
        )

    def load_smart_recommendations(self):
        self._apply_language()
        self._run_async(
            worker=self._build_smart_recommendations,
            on_success=lambda rows: self._render_results(rows, "Smart recommendations loaded"),
            loading_text="Building smart recommendations",
        )

    def _build_smart_recommendations(self):
        rows = []
        for release_id in self.history.get_ids()[:8]:
            try:
                release = self.client.by_id(release_id)
            except requests.RequestException:
                continue
            release["_reason"] = "Recently viewed"
            rows.append(release)

        for release in self.client.latest(limit=12):
            release["_reason"] = "Fresh release"
            rows.append(release)

        for release in self.client.random(limit=8):
            release["_reason"] = "Random pick"
            rows.append(release)

        deduped = []
        seen = set()
        for row in rows:
            rid = row.get("id")
            if rid in seen or rid is None:
                continue
            seen.add(rid)
            deduped.append(row)
            if len(deduped) >= 18:
                break
        return deduped

    @staticmethod
    def _annotate_reason(rows, reason):
        enriched = []
        for row in rows:
            current = dict(row)
            current["_reason"] = reason
            enriched.append(current)
        return enriched

    def _render_results(self, rows, done_status):
        self.tree.delete(*self.tree.get_children())
        self.release_map.clear()
        self._clear_episode_selector()

        for row in rows:
            norm = self._normalize_release(row)
            if norm["id"] is None:
                continue
            rid = str(norm["id"])
            self.release_map[rid] = norm
            self.tree.insert(
                "",
                tk.END,
                iid=rid,
                values=(
                    norm["title"],
                    norm["type"],
                    norm["year"],
                    norm["episodes"],
                    norm["reason"],
                ),
            )

        if not rows:
            self._set_status("No items found")
            self._set_detail_text("No results to show.")
            return

        children = self.tree.get_children()
        if not children:
            self._set_status("No valid items found")
            self._set_detail_text("No results to show.")
            return

        first = children[0]
        self.tree.selection_set(first)
        self.tree.focus(first)
        self.on_select_release()
        self._set_status(done_status)

    def _normalize_release(self, release):
        name = release.get("name", {})
        main_name = (name.get("main") or "").strip()
        english_name = (name.get("english") or "").strip()
        title = main_name or english_name or "Unknown title"
        if english_name and main_name and english_name.lower() != main_name.lower():
            title = f"{main_name} / {english_name}"

        rel_type = release.get("type", {})
        type_name = rel_type.get("value") or rel_type.get("description") or "?"
        year = release.get("year")
        reason = release.get("_reason", "Search")

        latest_episode = release.get("latest_episode")
        latest_ord = self._safe_int(latest_episode.get("ordinal") if isinstance(latest_episode, dict) else None)
        episodes_total = self._safe_int(release.get("episodes_total"))
        episodes_list = release.get("episodes")
        available_episode_numbers = self._extract_episode_ordinals(episodes_list)
        episode_streams = self._extract_episode_streams(episodes_list)
        external_player_url = self._normalize_external_player_url(release.get("external_player"))

        if available_episode_numbers and latest_ord is None:
            latest_ord = available_episode_numbers[-1]
        if available_episode_numbers and episodes_total is None:
            episodes_total = available_episode_numbers[-1]
        if available_episode_numbers and episodes_total is not None:
            episodes_total = max(episodes_total, available_episode_numbers[-1])

        if latest_ord is not None and episodes_total is not None:
            eps = f"{latest_ord}/{episodes_total}"
        elif latest_ord is not None:
            eps = str(latest_ord)
        elif episodes_total is not None:
            eps = str(episodes_total)
        elif isinstance(release.get("episodes"), list):
            eps = "0"
        else:
            eps = "?"

        return {
            "id": release.get("id"),
            "title": title,
            "type": str(type_name),
            "year": str(year) if year is not None else "?",
            "episodes": eps,
            "reason": reason,
            "description": release.get("description") or "No description.",
            "genres": [g.get("name") for g in release.get("genres", []) if isinstance(g, dict) and g.get("name")],
            "latest_episode_value": latest_ord,
            "episodes_total_value": episodes_total,
            "available_episode_numbers": available_episode_numbers,
            "episode_streams": episode_streams,
            "external_player_url": external_player_url,
            "manual_external_player_url": None,
            "selected_episode": None,
            "details_loaded": isinstance(release.get("episodes"), list),
        }

    @staticmethod
    def _safe_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _extract_episode_ordinals(episodes):
        if not isinstance(episodes, list):
            return []
        ordinals = []
        for episode in episodes:
            if not isinstance(episode, dict):
                continue
            ordinal = episode.get("ordinal")
            try:
                ordinal = int(ordinal)
            except (TypeError, ValueError):
                continue
            if ordinal > 0:
                ordinals.append(ordinal)
        return sorted(set(ordinals))

    @staticmethod
    def _extract_episode_streams(episodes):
        if not isinstance(episodes, list):
            return {}
        streams_by_episode = {}
        for episode in episodes:
            if not isinstance(episode, dict):
                continue
            ordinal = AniCliRuGui._safe_int(episode.get("ordinal"))
            if ordinal is None or ordinal <= 0:
                continue
            streams = {}
            for key in ("hls_2160", "hls_4k", "hls_1440", "hls_2k", "hls_1080", "hls_720", "hls_480", "hls_360"):
                value = episode.get(key)
                if isinstance(value, str) and value.strip():
                    streams[key] = value.strip()
            if streams:
                streams_by_episode[ordinal] = streams
        return streams_by_episode

    @staticmethod
    def _normalize_external_player_url(value):
        if not isinstance(value, str):
            return None
        url = value.strip()
        if not url:
            return None
        if url.startswith("//"):
            return f"https:{url}"
        return url

    def on_select_release(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        rid = selected[0]
        release = self.release_map.get(rid)
        if not release:
            return

        self.history.add(release["id"])
        self._populate_episode_selector(release)
        self._set_detail_text(self._format_detail(release))

        if release.get("details_loaded"):
            return

        self._run_async(
            worker=lambda rid=release["id"], reason=release["reason"]: self._load_release_details(rid, reason),
            on_success=lambda raw, tree_iid=rid: self._apply_release_details(tree_iid, raw),
            loading_text=f"Loading details: {release['title']}",
        )

    @staticmethod
    def _format_detail(release):
        lines = [
            f"Title: {release['title']}",
            f"Type: {release['type']}",
            f"Year: {release['year']}",
            f"Episodes: {release['episodes']}",
            f"Selected episode: {release['selected_episode']}" if release.get("selected_episode") else "Selected episode: -",
            (
                f"JP/Subs external: {'Available' if (release.get('external_player_url') or release.get('manual_external_player_url')) else 'Not available'}"
            ),
            f"Recommendation reason: {release['reason']}",
        ]
        if release["genres"]:
            lines.append(f"Genres: {', '.join(release['genres'])}")
        lines.append("")
        lines.append("Description:")
        lines.append(release["description"])
        return "\n".join(lines)

    def _set_detail_text(self, text):
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert("1.0", text)
        self.detail_text.config(state=tk.DISABLED)


def main():
    app = AniCliRuGui()
    app.mainloop()


if __name__ == "__main__":
    main()
