"""CompásZero — cuaderno de rimas para rap. Antes del beat, nace la idea.

Interfaz en Flet (Python + Flutter). La lógica vive en cz/: base de datos, sílabas, rimas,
ortografía, sinónimos, bases y búsqueda de bases libres.
"""
import asyncio
import json
import os
import re
import time

import flet as ft
import flet_audio as fa
import flet_audio_recorder as far

from cz import beats, discover, guide, inspiration
from cz.db import SECTIONS, STATUSES, Notebook
from cz.look import ACCENTS, FONTS, REC, TEXTURES, THEMES, Look
from cz.rhymes import TYPES, RhymeIndex, last_word, stress_info
from cz.rhymes import keys as rhyme_keys
from cz.spelling import Speller, Thesaurus
from cz.syllables import count_line, count_line_sung, sinalefas, words

try:
    from flet_speech import SpeechToText
except ImportError:  # en el PC sin la extensión
    SpeechToText = None

HERE = os.path.dirname(os.path.abspath(__file__))
INTRO_SECONDS = 8.4
RHYME_COLORS = ["#E5194B", "#F5A623", "#4FC3F7", "#9CCC65", "#BA68C8", "#FFD54F", "#4DB6AC", "#F48FB1"]
W = ft.Colors.with_opacity


def fmt_time(sec: float) -> str:
    sec = int(sec or 0)
    return f"{sec // 60}:{sec % 60:02d}"


def mounted(control) -> bool:
    """¿El control ya está en la página? (en Flet 1.x .page lanza error si no)."""
    try:
        return control.page is not None
    except RuntimeError:
        return False


def safe_update(*controls):
    for c in controls:
        if mounted(c):
            c.update()


def bpm_of(path: str, default: int = 90) -> int:
    m = re.search(r"(\d{2,3})\s*bpm", os.path.basename(path or "").lower())
    return int(m.group(1)) if m else default


class FakeSpeech:
    """Simula el dictado en el PC (CZ_FAKE_SPEECH=1) para probar la interfaz."""
    LINES = ["Antes del beat nace la idea", "rimo con el alma sin pedir permiso", "cada barra es un latido"]

    def __init__(self, app):
        self.app, self.on_result, self.on_status, self.on_error = app, None, None, None
        self.task = None

    async def initialize(self):
        return True

    async def listen(self, **kw):
        async def run():
            for line in self.LINES:
                ws = line.split()
                for i in range(1, len(ws) + 1):
                    await asyncio.sleep(.3)
                    self.on_result(type("E", (), {"text": " ".join(ws[:i]), "final": i == len(ws)})())
        self.task = asyncio.create_task(run())

    async def stop(self):
        if self.task:
            self.task.cancel()

    cancel = stop


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        data = os.getenv("CZ_DATA") or os.getenv("FLET_APP_STORAGE_DATA") or os.path.expanduser("~/.compaszero")
        os.makedirs(data, exist_ok=True)
        self.data_dir = data
        self.nb = Notebook(os.path.join(data, "cuaderno.db"))
        self.rhymes = RhymeIndex()
        self.speller = Speller(personal=self.nb.personal_words())
        self.thesaurus = Thesaurus()
        g = self.nb.get_setting
        if not g("jamendo_client_id"):
            try:
                with open(os.path.join(HERE, "assets", "config.json"), encoding="utf-8") as f:
                    cid = json.load(f).get("jamendo_client_id", "")
                if cid:
                    self.nb.set_setting("jamendo_client_id", cid)
            except (OSError, ValueError):
                pass
        self.L = Look(os.getenv("CZ_THEME") or g("theme", "Negro estudio"),
                      os.getenv("CZ_ACCENT") or g("accent", "Rojo REC"),
                      os.getenv("CZ_TEXTURE") or g("texture", "Grano"))
        # estado de navegación
        self.screen, self.tab = "intro", 0
        self.song_id = self.session_id = None
        self.section, self.rhyme_kind, self.query = "Verso", None, ""
        self.lesson = None
        self.fs_beat, self.fs_words = None, False
        self.discover_state = {"style": "Boom bap", "source": "Openverse", "query": "", "publish": False,
                               "results": [], "page": 1, "status": ""}
        # servicios nativos (se guardan referencias para que no se liberen)
        self.beat_audio = fa.Audio(release_mode=fa.ReleaseMode.LOOP, volume=.9)
        self.take_audio = fa.Audio(release_mode=fa.ReleaseMode.STOP)
        self.recorder = far.AudioRecorder()
        self.files = ft.FilePicker()
        self.share = ft.Share()
        if os.getenv("CZ_FAKE_SPEECH") or SpeechToText is None:
            self.speech = FakeSpeech(self)
        else:
            self.speech = SpeechToText()
        self.speech.on_result = self.on_speech_result
        self.speech.on_status = self.on_speech_status
        self.speech.on_error = self.on_speech_error
        self.speech_target = None  # "freestyle" o un callback de dictado
        self.beat_playing = None
        self.metronome_task = None
        self.recording_note = False

    # ================= estilo =================
    def apply_page_style(self):
        p, L = self.page, self.L
        p.fonts = FONTS
        p.theme_mode = ft.ThemeMode.LIGHT if L.light else ft.ThemeMode.DARK
        theme = ft.Theme(font_family="Poppins", color_scheme_seed=L.accent, use_material3=True)
        p.theme = p.dark_theme = theme
        p.bgcolor = L.bg
        p.padding = 0

    def txt(self, value, size=14, color=None, font="Poppins", weight=None, **kw):
        return ft.Text(value, size=size, color=color or self.L.text, font_family=font, weight=weight, **kw)

    def marker(self, value, size=18, color=None):
        """Títulos con letra de plumón (estilo grafiti)."""
        return ft.Text(value, size=size, color=color or self.L.accent, font_family="Marker")

    def card(self, content, on_click=None, padding=16, stripe=False, bg=None, margin=None):
        L = self.L
        inner = content
        if stripe:
            inner = ft.Row([ft.Container(width=4, height=40, bgcolor=L.accent, border_radius=4), ft.Container(content, expand=True)],
                           spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        return ft.Container(
            inner, padding=padding, margin=margin, on_click=on_click, ink=on_click is not None,
            bgcolor=bg or W(.94, L.surface), border_radius=22, border=ft.Border.all(1, W(.7, L.line)),
            shadow=ft.BoxShadow(blur_radius=22, spread_radius=-6, color=W(.10 if L.light else .55, "#000000"),
                                offset=ft.Offset(0, 8)))

    def button(self, text, on_click, primary=True, expand=False, icon=None, height=48):
        L = self.L
        row = [self.txt(text, 15, L.on_accent if primary else L.text, "PoppinsSemi")]
        if icon:
            row.insert(0, ft.Image(src=L.icon_on_accent(icon) if primary else L.icon(icon), width=22, height=22))
        return ft.Container(
            ft.Row(row, alignment=ft.MainAxisAlignment.CENTER, spacing=8), height=height, expand=expand,
            padding=ft.Padding.symmetric(horizontal=20), on_click=on_click, ink=True, border_radius=height / 2,
            bgcolor=L.accent if primary else W(.9, L.surface2),
            border=None if primary else ft.Border.all(1, L.line),
            shadow=ft.BoxShadow(blur_radius=18, spread_radius=-4, color=W(.45, L.accent), offset=ft.Offset(0, 6)) if primary else None)

    def chip(self, label, selected, on_click, small=False):
        L = self.L
        return ft.Container(
            self.txt(label, 12 if small else 13, L.on_accent if selected else L.text,
                     "PoppinsSemi" if selected else "PoppinsMedium"),
            padding=ft.Padding.symmetric(horizontal=14, vertical=7), border_radius=20, on_click=on_click, ink=True,
            bgcolor=L.accent if selected else W(.85, L.surface), border=ft.Border.all(1, L.accent if selected else L.line),
            animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT))

    def icon_btn(self, name, on_click, size=26, active=True, tooltip=None):
        return ft.Container(ft.Image(src=self.L.icon(name, active), width=size, height=size), padding=10, border_radius=40,
                            on_click=on_click, ink=True, tooltip=tooltip)

    def round_btn(self, name, on_click, size=56):
        L = self.L
        return ft.Container(ft.Image(src=L.icon_on_accent(name), width=size * .5, height=size * .5), width=size, height=size,
                            border_radius=size, bgcolor=L.accent, alignment=ft.Alignment.CENTER, on_click=on_click, ink=True,
                            shadow=ft.BoxShadow(blur_radius=20, spread_radius=-2, color=W(.5, L.accent), offset=ft.Offset(0, 6)))

    def header(self, title=None, back=None, actions=None):
        L = self.L
        left = [self.icon_btn("back", back)] if back else []
        if title:
            center = ft.Container(self.txt(title, 20, weight=None, font="PoppinsSemi", max_lines=1,
                                           overflow=ft.TextOverflow.ELLIPSIS), expand=True)
        else:
            center = ft.Container(ft.Image(src=L.wordmark(), height=54), expand=True, alignment=ft.Alignment.CENTER)
        return ft.Container(ft.Row(left + [center] + (actions or []), vertical_alignment=ft.CrossAxisAlignment.CENTER),
                            padding=ft.Padding.only(left=6, right=6, top=4, bottom=2))

    def snack(self, msg):
        self.page.show_dialog(ft.SnackBar(self.txt(msg, 14, "#FFFFFF"), bgcolor="#1E1E1E", duration=2500))

    # ================= render =================
    def background(self):
        L = self.L
        layers = [ft.Container(expand=True, bgcolor=L.bg)]
        tex = L.texture_src()
        if tex:
            layers.append(ft.Container(expand=True, image=ft.DecorationImage(
                src=tex, repeat=ft.ImageRepeat.REPEAT, opacity=.55 if L.light else .35, scale=1,
                color_filter=ft.ColorFilter(color="#000000" if L.light else "#FFFFFF", blend_mode=ft.BlendMode.SRC_IN))))
        # brillo cálido del color de acento arriba
        layers.append(ft.Container(expand=True, gradient=ft.RadialGradient(
            center=ft.Alignment(-0.9, -1.05), radius=1.25,
            colors=[W(.20 if not L.light else .14, L.accent), W(0, L.accent)])))
        if L.texture == "Cuaderno":
            layers.append(ft.Container(left=30, top=0, bottom=0, width=1.5, bgcolor=W(.35, L.accent)))
        return layers

    def render(self):
        p = self.page
        self.apply_page_style()
        p.controls.clear()
        p.floating_action_button = None
        if self.screen == "intro":
            body = self.intro_view()
        else:
            body = getattr(self, f"{self.screen}_view")()
        p.controls.append(ft.Stack(self.background() + [ft.SafeArea(body, expand=True)], expand=True))
        p.update()

    def go(self, screen, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
        if self.screen == "song" and screen != "song" and self.song_id:
            self.nb.snapshot(self.song_id)
        if screen != "song":
            self.page.run_task(self.stop_beat)
        self.screen = screen
        self.render()

    # ================= intro =================
    def intro_view(self):
        async def finish():
            await asyncio.sleep(INTRO_SECONDS)
            if self.screen == "intro":
                self.go("home")
        self.page.run_task(finish)
        return ft.Container(ft.Image(src="intro.webp", fit=ft.BoxFit.CONTAIN, width=340), expand=True,
                            alignment=ft.Alignment.CENTER, bgcolor="#000000", on_click=lambda e: self.go("home"))

    # ================= inicio =================
    def home_view(self):
        L = self.L
        settings = self.icon_btn("gear", lambda e: self.open_settings())
        top = self.header(actions=[settings])
        top.content.controls.insert(0, self.icon_btn("ideas_cuaderno", lambda e: self.go("guide"), tooltip="Aprende"))
        body = [self.songs_tab, self.ideas_tab, self.freestyle_tab][self.tab]()
        return ft.Column([top, ft.Container(body, expand=True), self.nav_bar()], spacing=0, expand=True)

    def nav_bar(self):
        L = self.L
        items = []
        for i, (name, ic) in enumerate([("Canciones", "canciones"), ("Ideas", "ideas"), ("Freestyle", "freestyle")]):
            active = i == self.tab
            items.append(ft.Container(
                ft.Column([
                    ft.Container(ft.Image(src=L.icon(ic, active), width=30, height=30), padding=ft.Padding.symmetric(vertical=6, horizontal=18),
                                 border_radius=20, bgcolor=W(.16, L.accent) if active else None,
                                 animate=ft.Animation(220, ft.AnimationCurve.EASE_OUT)),
                    self.txt(name, 11, L.text if active else L.muted, "PoppinsSemi" if active else "Poppins")],
                    spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
                expand=True, on_click=lambda e, i=i: self.go("home", tab=i), padding=ft.Padding.symmetric(vertical=6)))
        return ft.Container(ft.Row(items, spacing=0), margin=ft.Margin.only(left=14, right=14, bottom=10, top=4),
                            border_radius=28, bgcolor=W(.96, L.surface), border=ft.Border.all(1, L.line),
                            shadow=ft.BoxShadow(blur_radius=26, spread_radius=-6, color=W(.12 if L.light else .6, "#000000"),
                                                offset=ft.Offset(0, 10)))

    def songs_tab(self):
        L = self.L
        search = ft.TextField(value=self.query, hint_text="Buscar en títulos, letras y #etiquetas", border_radius=18,
                              filled=True, fill_color=W(.9, L.surface), border_color=L.line, focused_border_color=L.accent,
                              text_style=ft.TextStyle(font_family="Poppins", size=14, color=L.text),
                              hint_style=ft.TextStyle(color=L.muted, size=14), content_padding=ft.Padding.symmetric(vertical=14, horizontal=16),
                              prefix=ft.Image(src=L.icon("buscar"), width=20, height=20),
                              on_change=lambda e: self.search_changed(e.control.value))
        self.songs_list = ft.Column(spacing=12)
        self.fill_songs()
        fab = ft.Container(self.round_btn("plus", lambda e: self.new_song(), 62), right=20, bottom=14)
        return ft.Stack([ft.ListView([ft.Container(search, padding=ft.Padding.only(left=16, top=6, right=16, bottom=4)),
                                      ft.Container(self.songs_list, padding=ft.Padding.only(left=16, top=8, right=16, bottom=90))], expand=True), fab],
                        expand=True)

    def search_changed(self, value):
        self.query = value
        self.fill_songs()
        self.songs_list.update()

    def fill_songs(self):
        L = self.L
        songs = self.nb.search(self.query) if self.query.strip() else self.nb.songs()
        items = [] if self.query.strip() else [self.challenge_card()]
        for s in songs:
            status = ft.Container(self.txt(s.status, 11, L.accent, "PoppinsSemi"), border_radius=10,
                                  padding=ft.Padding.symmetric(vertical=3, horizontal=10), bgcolor=W(.14, L.accent))
            meta = f"{s.bars} barras" + (f"  ·  {s.tags}" if s.tags else "")
            items.append(self.card(ft.Column([
                ft.Row([self.txt(s.title, 17, font="PoppinsSemi", expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), status]),
                self.txt(meta, 12, L.muted)], spacing=4), on_click=lambda e, sid=s.id: self.go("song", song_id=sid), stripe=True))
        if self.query.strip() and not songs:
            items.append(ft.Container(self.txt("Nada encontrado.", 14, L.muted), padding=30, alignment=ft.Alignment.CENTER))
        if not self.query.strip() and not songs:
            items.append(ft.Container(self.txt("Tu primera canción empieza aquí.\nToca + para crearla.", 14, L.muted,
                                               text_align=ft.TextAlign.CENTER), padding=30, alignment=ft.Alignment.CENTER))
        self.songs_list.controls = items

    def challenge_card(self):
        L = self.L
        if not hasattr(self, "_challenge"):
            self._challenge = inspiration.daily()
        theme, word = self._challenge
        streak = self.nb.streak()

        def other(e):
            self._challenge = (inspiration.random_theme(), inspiration.random_word(word))
            self.fill_songs()
            self.songs_list.update()

        def start(e):
            sid = self.nb.create_song(self._challenge[0])
            self.nb.set_song(sid, tags=f"#reto #{self._challenge[1]}")
            self.go("song", song_id=sid)
        return ft.Container(ft.Column([
            ft.Row([self.marker("Reto del día", 17, L.on_accent),
                    ft.Container(self.txt(f"racha {streak} {'día' if streak == 1 else 'días'}", 11, L.on_accent, "PoppinsSemi"),
                                 bgcolor=W(.2, "#000000"), border_radius=10, padding=ft.Padding.symmetric(vertical=3, horizontal=10))],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.txt(theme, 19, L.on_accent, "PoppinsBold"),
            ft.Row([self.txt("Usa la palabra:", 13, W(.8, L.on_accent)), self.txt(word, 14, L.on_accent, "PoppinsBold")], spacing=6),
            ft.Row([ft.Container(self.txt("Escribir", 14, L.accent, "PoppinsSemi"), bgcolor=L.on_accent, border_radius=20,
                                 padding=ft.Padding.symmetric(vertical=9, horizontal=20), on_click=start, ink=True),
                    ft.Container(self.txt("Otro tema", 14, L.on_accent, "PoppinsMedium"), border_radius=20,
                                 padding=ft.Padding.symmetric(vertical=9, horizontal=16), on_click=other, ink=True,
                                 border=ft.Border.all(1, W(.5, L.on_accent)))], spacing=10)], spacing=6),
            padding=18, border_radius=24,
            gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT,
                                       colors=[L.accent, W(.75, L.accent)]),
            shadow=ft.BoxShadow(blur_radius=26, spread_radius=-6, color=W(.5, L.accent), offset=ft.Offset(0, 10)))

    def new_song(self):
        f = self.field("Título", autofocus=True)

        def create(e=None):
            self.page.pop_dialog()
            self.go("song", song_id=self.nb.create_song(f.value or ""))
        f.on_submit = create
        self.dialog("Nueva canción", f, [("Cancelar", None), ("Crear", create)])

    # ---------- ideas ----------
    def ideas_tab(self):
        L = self.L
        ideas, notes = self.nb.ideas(), self.nb.voice_notes()
        rec_label = "Detener nota de voz" if self.recording_note else "Grabar nota de voz"
        items = [self.button(rec_label, lambda e: self.page.run_task(self.toggle_voice_note), icon="voz")]
        if notes:
            items.append(self.marker("Notas de voz", 16))
            items += [self.take_card(t) for t in notes]
        if ideas:
            items.append(self.marker("Ideas sueltas", 16))
            items += [self.bar_row(b, lambda b: self.idea_sheet(b)) for b in ideas]
        if not ideas and not notes:
            items.append(ft.Container(self.txt("Anota frases sueltas o graba una nota de voz.\nLuego muévelas a una canción.",
                                               14, L.muted, text_align=ft.TextAlign.CENTER), padding=30,
                                      alignment=ft.Alignment.CENTER))
        lst = ft.ListView(items, spacing=10, padding=ft.Padding.only(left=16, top=6, right=16, bottom=10), expand=True)
        comp = self.composer("Escribe una barra…", lambda t: (self.nb.add_bar(t), self.render()),
                             context=lambda: ideas[0].text if ideas else "")
        return ft.Column([lst, comp], spacing=0, expand=True)

    # ---------- freestyle (lista) ----------
    def freestyle_tab(self):
        L = self.L
        items = [ft.Container(ft.Column([
            ft.Image(src=L.icon("freestyle"), width=54, height=54),
            self.txt("Elige una base, rapea y la app transcribe lo que dices.", 14, L.muted, text_align=ft.TextAlign.CENTER),
            self.button("Empezar freestyle", lambda e: self.go("freestyle"), icon="freestyle")],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12), padding=ft.Padding.symmetric(vertical=16, horizontal=10))]
        sessions = self.nb.sessions()
        if sessions:
            items.append(self.marker("Sesiones", 16))
        for x in sessions:
            when = time.strftime("%d/%m %H:%M", time.localtime(x.created_at))
            items.append(self.card(ft.Column([self.txt(x.beat, 16, font="PoppinsSemi"),
                                              self.txt(f"{when}  ·  {x.lines} líneas  ·  {fmt_time(x.duration)}", 12, L.muted)],
                                             spacing=3), on_click=lambda e, sid=x.id: self.go("review", session_id=sid), stripe=True))
        return ft.ListView(items, spacing=12, padding=ft.Padding.only(left=16, top=6, right=16, bottom=16), expand=True)

    # ================= piezas de escritura =================
    def field(self, label, value="", multiline=False, mono=False, autofocus=False, hint=None):
        L = self.L
        return ft.TextField(
            value=value, label=label, hint_text=hint, multiline=multiline, min_lines=3 if multiline else 1,
            max_lines=6 if multiline else 1, autofocus=autofocus, border_radius=16, filled=True,
            fill_color=W(.9, L.surface2), border_color=L.line, focused_border_color=L.accent,
            cursor_color=L.accent, label_style=ft.TextStyle(color=L.muted),
            text_style=ft.TextStyle(font_family="Mono" if mono else "Poppins", size=15, color=L.text),
            capitalization=ft.TextCapitalization.SENTENCES, autocorrect=True, enable_suggestions=True)

    def dialog(self, title, content, actions):
        L = self.L
        acts = []
        for label, cb in actions:
            danger = label.startswith("Borrar")
            acts.append(ft.TextButton(content=self.txt(label, 14, REC if danger else L.accent, "PoppinsSemi"),
                                      on_click=(lambda e, cb=cb: (self.page.pop_dialog(), cb and cb())) if cb != "keep"
                                      else None))
        dlg = ft.AlertDialog(title=self.txt(title, 19, font="PoppinsSemi"), content=content, actions=acts,
                             bgcolor=L.surface, shape=ft.RoundedRectangleBorder(radius=24))
        self.page.show_dialog(dlg)

    def sheet(self, content):
        L = self.L
        bs = ft.BottomSheet(ft.Container(content, padding=ft.Padding.only(left=20, top=8, right=20, bottom=24)), bgcolor=L.surface,
                            show_drag_handle=True, scrollable=True, dismissible=True)
        self.page.show_dialog(bs)
        return bs

    def spans(self, text, color=None):
        """Texto de una barra con la palabra final coloreada por rima y las dudosas subrayadas."""
        L = self.L
        tokens = re.split(r"([^\W\d_]+)", text)
        last = max((i for i in range(1, len(tokens), 2)), default=None)
        out = []
        for i, t in enumerate(tokens):
            if not t:
                continue
            if i % 2 == 0:
                out.append(ft.TextSpan(t))
            elif i == last and color:
                out.append(ft.TextSpan(t, style=ft.TextStyle(color=color, weight=ft.FontWeight.BOLD)))
            elif not self.speller.known(t):
                out.append(ft.TextSpan(t, style=ft.TextStyle(color="#FF8A80", decoration=ft.TextDecoration.UNDERLINE,
                                                            decoration_color="#FF8A80")))
            else:
                out.append(ft.TextSpan(t))
        return out

    def bar_row(self, bar, on_pick, color=None):
        L = self.L
        n = count_line_sung(bar.text)
        return ft.Container(ft.Row([
            ft.Text(spans=self.spans(bar.text, color), font_family="Mono", size=15, color=L.text, expand=True),
            ft.Container(self.txt(str(n), 11, L.muted, "Mono"), padding=ft.Padding.symmetric(vertical=3, horizontal=9), border_radius=10,
                         bgcolor=W(.9, L.surface2))], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(vertical=12, horizontal=14), border_radius=16, bgcolor=W(.9, L.surface),
            border=ft.Border.all(1, W(.6, L.line)), on_click=lambda e: on_pick(bar), ink=True)

    def rhyme_colors(self, bars):
        groups = {}
        for b in bars:
            k = rhyme_keys(last_word(b.text) or "")
            if k and k["asonante"]:
                groups.setdefault(k["asonante"], []).append(b.id)
        colors, n = {}, 0
        for ids in groups.values():
            if len(ids) >= 2:
                for i in ids:
                    colors[i] = RHYME_COLORS[n % len(RHYME_COLORS)]
                n += 1
        return colors

    def composer(self, hint, on_save, context=lambda: ""):
        """Escritura rápida con teclado nativo, contador de sílabas, dictado y modo rimas."""
        L = self.L
        count = self.txt("", 11, L.muted)
        title = self.txt("", 11, L.muted)
        suggest = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=6)
        rhyme_box = ft.Column([title, suggest], spacing=4, visible=self.rhyme_kind is not None)
        field = ft.TextField(
            hint_text=hint, expand=True, border_radius=22, filled=True, fill_color=W(.95, L.surface2),
            border_color=L.line, focused_border_color=L.accent, cursor_color=L.accent,
            text_style=ft.TextStyle(font_family="Mono", size=15, color=L.text), hint_style=ft.TextStyle(color=L.muted),
            content_padding=ft.Padding.symmetric(vertical=12, horizontal=16), capitalization=ft.TextCapitalization.SENTENCES,
            autocorrect=True, enable_suggestions=True, shift_enter=True)

        def insert(word):
            field.value = ((field.value or "").rstrip() + " " + word).lstrip() + " "
            field.update()
            refresh()

        def refresh(e=None):
            t = field.value or ""
            count.value = f"{count_line(t)} sílabas · {count_line_sung(t)} al rapear" if t.strip() else ""
            if self.rhyme_kind:
                target = last_word(t) or last_word(context())
                words_ = self.rhymes.find(target, self.rhyme_kind, 40) if target else []
                title.value = (f"{TYPES[self.rhyme_kind]} con «{target}»" if words_ else
                               (f"Sin rimas para «{target}»" if target else "Escribe una palabra para ver rimas"))
                suggest.controls = [ft.Container(self.txt(w, 13, L.text, "Mono"), padding=ft.Padding.symmetric(vertical=6, horizontal=12),
                                                 border_radius=12, bgcolor=W(.9, L.surface2), on_click=lambda e, w=w: insert(w),
                                                 ink=True) for w in words_]
            safe_update(count, rhyme_box)

        def submit(e=None):
            if (field.value or "").strip():
                on_save(field.value)

        def pick_kind(kind):
            self.rhyme_kind = None if self.rhyme_kind == kind else kind
            rhyme_box.visible = self.rhyme_kind is not None
            kinds.controls = kind_chips()
            kinds.update()
            refresh()

        def kind_chips():
            return ([self.txt("Rimas", 12, L.muted)] +
                    [self.chip(n, self.rhyme_kind == k, lambda e, k=k: pick_kind(k), small=True) for k, n in TYPES.items()] +
                    [self.chip("¿?", False, lambda e: self.go("guide"), small=True)])

        def dictate(e):
            async def go():
                ok = await self.speech.initialize()
                if not ok:
                    return self.snack("El dictado no está disponible en este teléfono")
                self.speech_target = lambda text: (setattr(field, "value", ((field.value or "") + " " + text).strip()),
                                                   field.update(), refresh())
                await self.speech.listen(locale="es_ES", pause_for=3, listen_for=30)
                self.snack("Te escucho…")
            self.page.run_task(go)
        field.on_change = refresh
        field.on_submit = submit
        kinds = ft.Row(kind_chips(), spacing=6, scroll=ft.ScrollMode.AUTO)
        refresh()
        send = self.round_btn("enviar", submit, 50)
        voice = self.icon_btn("voz", dictate, 26)
        return ft.Container(ft.Column([kinds, rhyme_box, ft.Row([field, voice, send], spacing=4,
                                                                 vertical_alignment=ft.CrossAxisAlignment.CENTER), count],
                                      spacing=6),
                            padding=ft.Padding.only(left=14, top=10, right=10, bottom=10), bgcolor=W(.97, L.surface),
                            border_radius=ft.BorderRadius.only(top_left=26, top_right=26),
                            border=ft.Border.only(top=ft.BorderSide(1, L.line)))

    def word_tools(self, f):
        """Toca una palabra: sinónimos y ortografía."""
        L = self.L
        chips = ft.Row(wrap=True, spacing=6, run_spacing=6)
        panel = ft.Column(spacing=6)

        def replace(old, new):
            f.value = re.sub(rf"\b{re.escape(old)}\b", new, f.value, count=1)
            f.update()
            build()

        def show(w):
            panel.controls.clear()
            opts = []
            if not self.speller.known(w):
                panel.controls.append(self.txt(f"«{w}» no está en el diccionario", 13, "#FF8A80"))
                opts = self.speller.suggest(w)

                def add(e, w=w):
                    self.nb.add_word(w)
                    self.speller.personal.add(w.lower())
                    build()
                panel.controls.append(ft.TextButton(content=self.txt("+ Agregar a mi diccionario", 13, L.accent), on_click=add))
            syn = self.thesaurus.synonyms(w)
            if syn:
                panel.controls.append(self.txt(f"Sinónimos de «{w}»", 12, L.muted))
            opts += syn[:18]
            panel.controls.append(ft.Row([ft.Container(self.txt(o, 13, L.text, "Mono"), padding=ft.Padding.symmetric(vertical=5, horizontal=11),
                                                       border_radius=12, bgcolor=W(.9, L.surface2), ink=True,
                                                       on_click=lambda e, o=o: replace(w, o)) for o in opts],
                                         wrap=True, spacing=6, run_spacing=6))
            panel.update()

        def build(e=None):
            seen = []
            for w in words(f.value or ""):
                if w not in seen and len(seen) < 16:
                    seen.append(w)
            chips.controls = [ft.Container(self.txt(w, 12, "#FF8A80" if not self.speller.known(w) else L.text, "PoppinsMedium"),
                                           padding=ft.Padding.symmetric(vertical=5, horizontal=12), border_radius=14,
                                           border=ft.Border.all(1, L.line), on_click=lambda e, w=w: show(w), ink=True)
                              for w in seen]
            panel.controls.clear()
            safe_update(chips, panel)
        build()
        return ft.Column([self.txt("Toca una palabra: sinónimos y ortografía", 12, L.muted), chips, panel], spacing=8), build

    def bar_sheet(self, bar, title, extra=None, on_save=None, on_delete=None):
        L = self.L
        f = self.field("Barra", bar.text, multiline=True, mono=True)
        info = self.txt(f"{count_line(bar.text)} sílabas · {count_line_sung(bar.text)} al rapear", 12, L.muted)
        tools, rebuild = self.word_tools(f)

        def changed(e):
            info.value = f"{count_line(f.value)} sílabas · {count_line_sung(f.value)} al rapear"
            info.update()
            rebuild()
        f.on_change = changed
        holder = {}

        def close_then(cb):
            def h(e):
                self.page.pop_dialog()
                cb(f.value)
            return h
        actions = ft.Row([ft.TextButton(content=self.txt("Borrar", 14, REC, "PoppinsSemi"), on_click=close_then(lambda v: on_delete())),
                          ft.Container(expand=True),
                          self.button("Guardar", close_then(on_save), height=42)])
        content = ft.Column([self.txt(title, 19, font="PoppinsSemi"), f, info, tools] + (extra(f) if extra else []) + [actions],
                            spacing=12, tight=True)
        holder["s"] = self.sheet(content)

    def idea_sheet(self, bar):
        L = self.L
        songs = self.nb.songs()
        state = {"section": "Verso"}

        def extra(f):
            if not songs:
                return []
            row = ft.Row(spacing=6, wrap=True)

            def draw():
                row.controls = [self.chip(s, state["section"] == s, lambda e, s=s: (state.update(section=s), draw(), row.update()), True)
                                for s in SECTIONS]
            draw()

            def move(sid):
                self.page.pop_dialog()
                self.nb.update_bar(bar.id, f.value)
                self.nb.move_idea(bar.id, sid, state["section"])
                self.render()
                self.snack("Idea movida a la canción")
            return [self.marker("Mover a canción", 15), row] + [
                ft.TextButton(content=self.txt(f"→  {s.title}", 14, L.text), on_click=lambda e, sid=s.id: move(sid)) for s in songs]
        self.bar_sheet(bar, "Idea", extra, on_save=lambda v: (self.nb.update_bar(bar.id, v), self.render()),
                       on_delete=lambda: (self.nb.delete_bar(bar.id), self.render()))

    # ================= canción =================
    def song_view(self):
        L = self.L
        song = self.nb.song(self.song_id)
        if not song:
            self.screen = "home"
            return self.home_view()
        title = ft.Container(self.txt(song.title, 20, font="PoppinsSemi", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                             expand=True, on_click=lambda e: self.rename(song))
        top = ft.Container(ft.Row([self.icon_btn("back", lambda e: self.go("home")), title,
                                   self.icon_btn("mas", lambda e: self.song_menu(song))],
                                  vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=ft.Padding.only(left=6, top=4, right=6, bottom=2))
        bars = self.nb.bars(song.id)
        colors = self.rhyme_colors(bars)
        groups = {}
        for b in bars:
            groups.setdefault(b.section or "Sin sección", []).append(b)
        items = [self.beat_strip(song)]
        tags = []
        if song.status:
            tags.append(ft.Container(self.txt(song.status, 11, L.accent, "PoppinsSemi"), border_radius=10,
                                     padding=ft.Padding.symmetric(vertical=3, horizontal=10), bgcolor=W(.14, L.accent)))
        if song.tags:
            tags.append(self.txt(song.tags, 12, L.muted))
        items.append(ft.Row(tags, spacing=8))
        spb = 4 * 60 / max(song.bpm, 40)
        for name in SECTIONS + [k for k in groups if k not in SECTIONS]:
            if name in groups:
                n = len(groups[name])
                items.append(ft.Row([self.marker(name, 18), self.txt(f"{n} compases ≈ {fmt_time(n * spb)}", 11, L.muted)],
                                    vertical_alignment=ft.CrossAxisAlignment.END, spacing=10))
                items += [self.bar_row(b, self.edit_bar, colors.get(b.id)) for b in groups[name]]
        takes = self.nb.takes(song.id)
        if takes:
            items.append(self.marker("Tomas", 18))
            items += [self.take_card(t) for t in takes]
        if not bars:
            items.append(ft.Container(self.txt("Escribe la primera barra abajo.", 14, L.muted), padding=30,
                                      alignment=ft.Alignment.CENTER))
        lst = ft.ListView(items, spacing=10, padding=ft.Padding.only(left=16, top=4, right=16, bottom=12), expand=True)
        secs = ft.Row([self.chip(s, self.section == s, lambda e, s=s: self.go("song", section=s), small=True) for s in SECTIONS],
                      spacing=6, scroll=ft.ScrollMode.AUTO)
        comp = self.composer(f"Barra en {self.section}…", lambda t: (self.nb.add_bar(t, song.id, self.section), self.render()),
                             context=lambda: bars[-1].text if bars else "")
        comp.content.controls.insert(0, secs)
        return ft.Column([top, lst, comp], spacing=0, expand=True)

    def beat_strip(self, song):
        L = self.L
        name = os.path.splitext(os.path.basename(song.beat))[0] if song.beat else "Sin base · toca para elegir"
        playing = self.beat_playing == song.beat and song.beat
        self.metro = [ft.Container(width=10, height=10, border_radius=10, bgcolor=L.line,
                                   animate=ft.Animation(120, ft.AnimationCurve.EASE_OUT)) for _ in range(4)]

        async def toggle(e):
            if self.beat_playing == song.beat and song.beat:
                await self.stop_beat()
            elif not song.beat:
                return self.pick_song_beat(song)
            else:
                await self.play_beat(song.beat, song.bpm)
            self.render()
        return self.card(ft.Row([
            ft.Container(ft.Image(src=L.icon("stop" if playing else "play"), width=34, height=34), on_click=toggle, ink=True,
                         border_radius=30, padding=4),
            ft.Container(ft.Column([self.txt(name, 14, font="PoppinsMedium", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    self.txt(f"{song.bpm} BPM", 11, L.muted)], spacing=0), expand=True,
                         on_click=lambda e: self.pick_song_beat(song)),
            ft.Row(self.metro, spacing=5)], vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=10)

    async def play_beat(self, path, bpm, on_beat=None):
        await self.stop_beat()
        self.beat_audio.src = path
        self.beat_audio.update()
        await self.beat_audio.play()
        self.beat_playing = path
        self.metronome_task = asyncio.create_task(self.metronome(bpm, on_beat))

    async def metronome(self, bpm, on_beat=None):
        n = 0
        step = 60.0 / max(bpm, 40)
        t0 = time.monotonic()
        try:
            while True:
                n += 1
                metro = getattr(self, "metro", [])
                if metro and mounted(metro[0]):
                    for i, m in enumerate(metro):
                        m.bgcolor = (self.L.accent if (n - 1) % 4 == 0 else self.L.text) if i == (n - 1) % 4 else self.L.line
                    self.page.update()
                if on_beat:
                    await on_beat(n)
                await asyncio.sleep(max(0, t0 + n * step - time.monotonic()))
        except asyncio.CancelledError:
            pass

    async def stop_beat(self):
        if self.metronome_task:
            self.metronome_task.cancel()
            self.metronome_task = None
        if self.beat_playing:
            try:
                await self.beat_audio.pause()
            except Exception:
                pass
        self.beat_playing = None

    def edit_bar(self, bar):
        self.bar_sheet(bar, "Editar barra", on_save=lambda v: (self.nb.update_bar(bar.id, v), self.render()),
                       on_delete=lambda: (self.nb.delete_bar(bar.id), self.render()))

    def rename(self, song):
        f = self.field("Título", song.title, autofocus=True)
        self.dialog("Título", f, [("Cancelar", None), ("Guardar", lambda: (self.nb.rename_song(song.id, f.value), self.render()))])

    def song_menu(self, song):
        L = self.L
        st = ft.Row(spacing=6, wrap=True, run_spacing=6)

        def draw():
            cur = self.nb.song(song.id).status
            st.controls = [self.chip(x, cur == x, lambda e, x=x: (self.nb.set_song(song.id, status=x), draw(), st.update()), True)
                           for x in STATUSES]
        draw()
        tags = self.field("#etiquetas", song.tags, hint="#barrio #amor")
        tags.on_blur = lambda e: self.nb.set_song(song.id, tags=(tags.value or "").strip())

        def item(icon, text, cb, danger=False):
            def h(e):
                self.nb.set_song(song.id, tags=(tags.value or "").strip())
                self.page.pop_dialog()
                cb()
            return ft.Container(ft.Row([ft.Image(src=L.icon(icon), width=24, height=24),
                                        self.txt(text, 15, REC if danger else L.text, "PoppinsMedium")], spacing=14),
                                padding=ft.Padding.symmetric(vertical=12, horizontal=6), on_click=h, ink=True, border_radius=12)
        content = ft.Column([
            self.txt(song.title, 19, font="PoppinsSemi"), self.txt("Estado", 12, L.muted), st, tags,
            item("freestyle", "Grabar con teleprompter", lambda: self.go("prompter", song_id=song.id)),
            item("play", "Elegir base y BPM", lambda: self.pick_song_beat(song)),
            item("ideas", "Versiones anteriores", lambda: self.show_versions(song)),
            item("enviar", "Compartir letra", lambda: self.page.run_task(self.share_song, song)),
            item("mas", "Borrar canción", lambda: self.confirm_delete(song), True),
        ], spacing=8, tight=True)
        self.sheet(content)

    async def share_song(self, song):
        await self.share.share_text(self.nb.song_text(song.id), subject=song.title)

    def confirm_delete(self, song):
        self.dialog(f"¿Borrar «{song.title}»?", self.txt("Se borran también sus barras y tomas.", 14, self.L.muted),
                    [("Cancelar", None), ("Borrar", lambda: (self.nb.delete_song(song.id), self.go("home")))])

    def pick_song_beat(self, song):
        L = self.L
        state = {"beat": song.beat}
        bpm = self.field("BPM", str(song.bpm))
        bpm.keyboard_type = ft.KeyboardType.NUMBER
        row = ft.Row(spacing=6, wrap=True, run_spacing=6)

        def draw():
            row.controls = [self.chip(n, p == state["beat"], lambda e, p=p: pick(p), True) for n, p in beats.list_beats(self.data_dir)]

        def pick(p):
            state["beat"] = p
            bpm.value = str(bpm_of(p, int(bpm.value or 90)))
            draw()
            row.update()
            bpm.update()
        draw()

        def save():
            try:
                v = max(40, min(220, int(bpm.value or 90)))
            except ValueError:
                v = 90
            self.page.run_task(self.stop_beat)
            self.nb.set_song(song.id, beat=state["beat"] or "", bpm=v)
            self.render()
        self.dialog("Base de la canción", ft.Column([row, self.txt("El BPM se lee del nombre de la base si lo tiene", 12, L.muted), bpm],
                                                    tight=True, spacing=10, scroll=ft.ScrollMode.AUTO, height=360),
                    [("Cancelar", None), ("Guardar", save)])

    def show_versions(self, song):
        L = self.L
        self.nb.snapshot(song.id)
        vs = self.nb.versions(song.id)[1:]
        items = []
        for v in vs:
            lines = json.loads(v.content)
            when = time.strftime("%d/%m %H:%M", time.localtime(v.created_at))

            def restore(e, v=v, when=when):
                self.page.pop_dialog()
                self.dialog(f"¿Volver a la versión del {when}?", self.txt("La letra actual queda en el historial.", 14, L.muted),
                            [("Cancelar", None), ("Restaurar", lambda: (self.nb.restore(v.id), self.render()))])
            items.append(self.card(ft.Column([self.txt(f"{when} · {len(lines)} barras", 14, font="PoppinsSemi"),
                                              self.txt(" / ".join(t for _, t in lines[:2])[:70], 12, L.muted)], spacing=2),
                                   on_click=restore, padding=12))
        if not items:
            items = [self.txt("Todavía no hay versiones anteriores. Se guarda una cada vez que sales de la canción con cambios.",
                              14, L.muted)]
        self.sheet(ft.Column([self.txt("Versiones", 19, font="PoppinsSemi")] + items, spacing=10, tight=True))

    # ================= tomas y notas de voz =================
    def take_card(self, t):
        L = self.L
        when = time.strftime("%d/%m %H:%M", time.localtime(t.created_at))

        async def play(e):
            self.take_audio.src = t.path
            self.take_audio.update()
            await self.take_audio.play()

        def delete(e):
            self.dialog("¿Borrar esta grabación?", self.txt(t.name, 14, L.muted),
                        [("Cancelar", None), ("Borrar", lambda: (self.nb.delete_take(t.id), self.render()))])
        return self.card(ft.Row([
            ft.Container(ft.Image(src=L.icon("play"), width=30, height=30), on_click=play, ink=True, border_radius=30, padding=4),
            ft.Column([self.txt(t.name or "Toma", 15, font="PoppinsSemi"), self.txt(f"{fmt_time(t.duration)} · {when}", 12, L.muted)],
                      spacing=0, expand=True),
            ft.Container(self.txt("Borrar", 12, REC), on_click=delete, padding=8)],
            vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=10)

    def takes_dir(self):
        d = os.path.join(self.data_dir, "tomas")
        os.makedirs(d, exist_ok=True)
        return d

    async def start_recording(self, path) -> bool:
        if not await self.recorder.has_permission():
            self.snack("Sin permiso de micrófono")
            return False
        cfg = far.AudioRecorderConfiguration(encoder=far.AudioEncoder.AACLC)
        return await self.recorder.start_recording(output_path=path, configuration=cfg)

    async def toggle_voice_note(self):
        if self.recording_note:
            path = await self.recorder.stop_recording()
            dur = time.monotonic() - self._note_t0
            self.recording_note = False
            if path:
                self.nb.add_take(path, dur, name=f"Nota de voz {len(self.nb.voice_notes()) + 1}")
            return self.render()
        path = os.path.join(self.takes_dir(), f"nota_{int(time.time())}.m4a")
        if await self.start_recording(path):
            self.recording_note, self._note_t0 = True, time.monotonic()
            self.render()

    # ================= voz =================
    def on_speech_result(self, e):
        if self.speech_target == "freestyle":
            self.fs_on_result(e.text, e.final)
        elif callable(self.speech_target) and e.final:
            target, self.speech_target = self.speech_target, None
            target(e.text)

    def on_speech_status(self, e):
        # el reconocedor de Android se detiene tras cada pausa: en freestyle lo reiniciamos
        if self.speech_target == "freestyle" and getattr(self, "fs_running", False) and e.status in ("done", "notListening"):
            self.page.run_task(self.speech.listen, locale="es_ES", pause_for=4, listen_for=120)

    def on_speech_error(self, e):
        if self.speech_target == "freestyle" and getattr(self, "fs_running", False):
            if not e.permanent or "no_match" in e.message or "speech_timeout" in e.message:
                self.page.run_task(self.speech.listen, locale="es_ES", pause_for=4, listen_for=120)
                return
        self.snack(f"Voz: {e.message}")

    # ================= freestyle =================
    def freestyle_view(self):
        L = self.L
        lst = beats.list_beats(self.data_dir)
        if self.fs_beat not in [p for _, p in lst]:
            self.fs_beat = lst[0][1] if lst else None
        self.fs_running = getattr(self, "fs_running", False)
        chips = ft.Row([self.chip(n[:26], p == self.fs_beat, lambda e, p=p: self.go("freestyle", fs_beat=p), True) for n, p in lst],
                       spacing=6, scroll=ft.ScrollMode.AUTO)
        c = discover.credits_for(self.fs_beat) if self.fs_beat else None
        credit = self.txt(f"«{c['title']}» de {c['artist']} · {discover.license_label(c['license'])}" if c else "", 11, L.muted)
        self.fs_lines = ft.ListView(spacing=6, expand=True, auto_scroll=True, padding=ft.Padding.symmetric(vertical=6, horizontal=18))
        self.fs_partial = self.txt("", 15, L.muted, "Mono", italic=True)
        self.fs_word = ft.Text("", size=30, font_family="Marker", color=L.accent)
        self.fs_clock = self.txt("Toca para empezar", 14, L.muted, "PoppinsMedium")
        self.fs_dot = ft.Container(width=52, height=52, border_radius=52, bgcolor=REC,
                                   animate=ft.Animation(700, ft.AnimationCurve.EASE_IN_OUT))
        rec = ft.Container(self.fs_dot, width=96, height=96, border_radius=96, border=ft.Border.all(4, L.text),
                           alignment=ft.Alignment.CENTER, on_click=lambda e: self.page.run_task(self.fs_toggle), ink=True)
        words_chip = self.chip("Palabras al azar", self.fs_words,
                               lambda e: (setattr(self, "fs_words", not self.fs_words), self.render()), True)
        top = self.header("Freestyle", back=lambda e: self.page.run_task(self.fs_leave),
                          actions=[self.icon_btn("descubrir", lambda e: self.go("discover")),
                                   self.icon_btn("importar", lambda e: self.page.run_task(self.import_beat))])
        return ft.Column([
            top, ft.Container(chips, padding=ft.Padding.symmetric(vertical=0, horizontal=16)), ft.Container(credit, padding=ft.Padding.symmetric(vertical=2, horizontal=18)),
            ft.Container(ft.Column([self.fs_lines, ft.Container(self.fs_partial, padding=ft.Padding.symmetric(vertical=0, horizontal=18))], expand=True),
                         expand=True),
            ft.Row([words_chip, self.fs_word], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.txt("Usa audífonos: así el micrófono escucha tu voz y no la pista.", 12, L.muted, text_align=ft.TextAlign.CENTER),
            ft.Column([rec, self.fs_clock], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            ft.Container(height=14)], spacing=8, expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    async def fs_toggle(self):
        if self.fs_running:
            return await self.fs_stop()
        if not self.fs_beat:
            return self.snack("Importa o descubre una base primero")
        if not await self.speech.initialize():
            return self.snack("El reconocimiento de voz no está disponible")
        name = os.path.splitext(os.path.basename(self.fs_beat))[0]
        self.session_id = self.nb.start_session(name)
        self.fs_running, self.fs_t0 = True, time.monotonic()
        self.speech_target = "freestyle"
        bpm = bpm_of(self.fs_beat)
        every = 8 * 4  # palabra nueva cada 8 compases

        async def on_beat(n):
            if not self.fs_running:
                return
            self.fs_clock.value = f"REC  {fmt_time(time.monotonic() - self.fs_t0)}"
            self.fs_clock.color = REC
            self.fs_dot.bgcolor = "#3D0712" if n % 2 else REC
            if self.fs_words and (n - 1) % every == 0:
                self.fs_word.value = inspiration.random_word(self.fs_word.value)
            self.page.update()
        await self.play_beat(self.fs_beat, bpm, on_beat)
        await self.speech.listen(locale="es_ES", pause_for=4, listen_for=120)

    def fs_on_result(self, text, final):
        if not self.fs_running:
            return
        if final and text.strip():
            t = time.monotonic() - self.fs_t0
            self.nb.add_line(self.session_id, t, text)
            self.fs_lines.controls.append(ft.Text(spans=[ft.TextSpan(fmt_time(t) + "  ", ft.TextStyle(color=self.L.muted)),
                                                         ft.TextSpan(text)], font_family="Mono", size=15, color=self.L.text))
            self.fs_partial.value = ""
        else:
            self.fs_partial.value = text
        self.page.update()

    async def fs_stop(self, review=True):
        if not self.fs_running:
            return
        self.fs_running = False
        self.speech_target = None
        await self.speech.stop()
        await self.stop_beat()
        self.nb.end_session(self.session_id, time.monotonic() - self.fs_t0)
        if review:
            self.go("review", session_id=self.session_id)

    async def fs_leave(self):
        await self.fs_stop(review=False)
        self.go("home", tab=2)

    async def import_beat(self):
        files = await self.files.pick_files(dialog_title="Elige una base", file_type=ft.FilePickerFileType.CUSTOM,
                                            allowed_extensions=["mp3", "wav", "ogg", "m4a", "aac", "flac"])
        if files and files[0].path:
            self.fs_beat = beats.import_beat(self.data_dir, files[0].path)
            self.render()

    # ================= revisión =================
    def review_view(self):
        L = self.L
        s = self.nb.session(self.session_id)
        if not s:
            return self.home_view()
        lines = self.nb.lines(s.id)

        def edit(line):
            bar = type("B", (), {"id": line.id, "text": line.text})()
            self.bar_sheet(bar, f"Línea en {fmt_time(line.t)}",
                           extra=lambda f: [ft.TextButton(content=self.txt("Enviar a Ideas", 14, L.accent),
                                                          on_click=lambda e: (self.page.pop_dialog(), self.nb.add_bar(f.value),
                                                                              self.snack("Enviada a Ideas")))],
                           on_save=lambda v: (self.nb.update_line(line.id, v), self.render()),
                           on_delete=lambda: (self.nb.delete_line(line.id), self.render()))
        rows = []
        for l in lines:
            r = self.bar_row(type("B", (), {"id": l.id, "text": l.text})(), lambda b, l=l: edit(l))
            r.content.controls.insert(0, self.txt(fmt_time(l.t), 11, L.muted, "Mono"))
            rows.append(r)

        def to_ideas(e):
            for l in lines:
                self.nb.add_bar(l.text)
            self.snack(f"{len(lines)} líneas en Ideas")

        def to_song(e):
            sid = self.nb.create_song(f"Freestyle {time.strftime('%d/%m', time.localtime(s.created_at))}")
            for l in lines:
                self.nb.add_bar(l.text, sid, "Verso")
            self.go("song", song_id=sid)
        delete = self.icon_btn("mas", lambda e: self.dialog("¿Borrar este freestyle?", self.txt(s.beat, 14, L.muted), [
            ("Cancelar", None), ("Borrar", lambda: (self.nb.delete_session(s.id), self.go("home", tab=2)))]))
        body = ft.ListView(rows or [ft.Container(self.txt("No se transcribió nada.\nPrueba hablar más cerca del micrófono.", 14,
                                                         L.muted, text_align=ft.TextAlign.CENTER), padding=30)],
                           spacing=8, padding=ft.Padding.symmetric(vertical=6, horizontal=16), expand=True)
        acts = ft.Container(ft.Row([self.button("Todo a Ideas", to_ideas, primary=False, expand=True),
                                    self.button("Nueva canción", to_song, expand=True)], spacing=10),
                            padding=ft.Padding.all(14), visible=bool(lines))
        return ft.Column([self.header(f"Revisión · {s.beat}", back=lambda e: self.go("home", tab=2), actions=[delete]), body, acts],
                         spacing=0, expand=True)

    # ================= descubrir bases =================
    def discover_view(self):
        L, st = self.L, self.discover_state
        q = ft.TextField(value=st["query"], hint_text="Buscar: oscuro, piano, 90s…", expand=True, border_radius=18, filled=True,
                         fill_color=W(.9, L.surface), border_color=L.line, focused_border_color=L.accent,
                         text_style=ft.TextStyle(size=14, color=L.text), content_padding=ft.Padding.symmetric(vertical=12, horizontal=14))

        def new_search(e=None):
            st.update(query=q.value or "", results=[], page=1)
            self.render()
            self.run_search()
        q.on_submit = new_search

        def setv(k, v):
            st[k] = v
            new_search()
        styles = ft.Row([self.chip(s, st["style"] == s, lambda e, s=s: setv("style", s), True) for s in discover.STYLES],
                        spacing=6, scroll=ft.ScrollMode.AUTO)
        srcs = ft.Row([self.chip(s, st["source"] == s, lambda e, s=s: setv("source", s), True) for s in ("Openverse", "Jamendo")] +
                      [self.chip("Solo para publicar", st["publish"], lambda e: setv("publish", not st["publish"]), True)],
                      spacing=6, scroll=ft.ScrollMode.AUTO)
        self.d_status = self.txt(st["status"], 12, L.muted)
        self.d_list = ft.ListView(spacing=10, padding=ft.Padding.symmetric(vertical=6, horizontal=16), expand=True)
        self.fill_discover()
        if not st["results"] and not st["status"]:
            self.run_search()
        return ft.Column([
            self.header("Descubrir bases", back=lambda e: self.page.run_task(self.leave_discover)),
            ft.Container(ft.Row([q, self.round_btn("buscar", new_search, 46)], spacing=8), padding=ft.Padding.symmetric(vertical=0, horizontal=16)),
            ft.Container(styles, padding=ft.Padding.symmetric(vertical=0, horizontal=16)), ft.Container(srcs, padding=ft.Padding.symmetric(vertical=0, horizontal=16)),
            ft.Container(self.d_status, padding=ft.Padding.symmetric(vertical=0, horizontal=18)), self.d_list,
            ft.Container(self.txt("Bases con licencia Creative Commons: se guarda autor y licencia para darle crédito.", 11,
                                  L.muted, text_align=ft.TextAlign.CENTER), padding=ft.Padding.symmetric(vertical=6, horizontal=16))],
            spacing=8, expand=True)

    async def leave_discover(self):
        await self.take_audio.pause()
        self.go("freestyle")

    def run_search(self):
        st = self.discover_state
        st["status"] = f"Buscando en {st['source']}…"

        def done(res, err):
            st["status"] = err or (f"{len(st['results']) + len(res)} bases" if (st["results"] or res)
                                   else "Sin resultados: prueba otro estilo o fuente")
            st["results"] += res
            if err and "Jamendo" in err:
                self.open_settings()
            if self.screen == "discover":
                self.d_status.value = st["status"]
                self.fill_discover()
                self.page.update()
        self.nb.count_request(st["source"])
        discover.search(st["source"], st["style"], st["query"], self.nb.get_setting("jamendo_client_id"), st["publish"],
                        st["page"], done)

    def fill_discover(self):
        L, st = self.L, self.discover_state
        folder = beats.user_dir(self.data_dir)
        items = []
        for t in st["results"]:
            have = os.path.exists(os.path.join(folder, discover.safe_name(t) + ".mp3"))
            pub = ft.Container(self.txt("sirve para publicar" if t["publish_ok"] else "solo uso personal", 10,
                                        "#141414", "PoppinsSemi"), bgcolor="#9CCC65" if t["publish_ok"] else "#F5A623",
                               border_radius=8, padding=ft.Padding.symmetric(vertical=2, horizontal=8))
            dl_btn = self.button("Descargada" if have else "Descargar", None, primary=not have, height=38, expand=True)
            if not have:
                dl_btn.on_click = lambda e, t=t, b=dl_btn: self.download_beat(t, b)

            async def preview(e, t=t):
                self.take_audio.src = t["stream"]
                self.take_audio.update()
                await self.take_audio.play()
            dur = fmt_time(t["duration"]) if t["duration"] else "—"
            items.append(self.card(ft.Column([
                self.txt(t["title"], 15, font="PoppinsSemi", max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Row([self.txt(f"{t['artist']} · {dur} · {discover.license_label(t['license'])}", 12, L.muted, expand=True,
                                 max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), pub]),
                self.txt(t["source"], 11, L.muted),
                ft.Row([self.button("Escuchar", preview, primary=False, height=38, icon="play", expand=True), dl_btn], spacing=8)],
                spacing=6), padding=14))
        if st["results"]:
            def more(e):
                st["page"] += 1
                self.run_search()
            items.append(ft.TextButton(content=self.txt("Más resultados", 14, L.accent, "PoppinsSemi"), on_click=more))
        self.d_list.controls = items

    def download_beat(self, t, btn):
        btn.content.controls[-1].value = "Bajando… 0%"
        btn.update()

        def progress(p):
            btn.content.controls[-1].value = f"Bajando… {int(p * 100)}%"
            btn.update()

        def done(path, err):
            btn.content.controls[-1].value = "Reintentar" if err else "Descargada"
            self.d_status.value = f"No se pudo descargar: {err}" if err else "Lista: ya aparece en Freestyle y en las canciones"
            self.page.update()
        discover.download(t, beats.user_dir(self.data_dir), done, progress)

    # ================= teleprompter =================
    def prompter_view(self):
        L = self.L
        song = self.nb.song(self.song_id)
        self.p_rows = []
        items = []
        current = None
        for b in self.nb.bars(song.id):
            if b.section != current:
                current = b.section
                items.append(self.marker(current or "", 18))
            t = ft.Text(b.text, size=24, font_family="Mono", color=L.muted, animate_opacity=200)
            self.p_rows.append(t)
            items.append(t)
        items.append(ft.Container(height=300))
        self.p_list = ft.ListView(items, spacing=14, padding=ft.Padding.symmetric(vertical=10, horizontal=22), expand=True)
        beat = os.path.splitext(os.path.basename(song.beat))[0] if song.beat else "sin base (solo voz)"
        self.p_status = self.txt(f"{beat} · {song.bpm} BPM · una barra por compás", 13, L.muted, text_align=ft.TextAlign.CENTER)
        self.p_dot = ft.Container(width=52, height=52, border_radius=52, bgcolor=REC, animate=ft.Animation(500))
        rec = ft.Container(self.p_dot, width=96, height=96, border_radius=96, border=ft.Border.all(4, L.text),
                           alignment=ft.Alignment.CENTER, on_click=lambda e: self.page.run_task(self.p_toggle), ink=True)
        self.p_running = False
        return ft.Column([self.header(f"Grabar · {song.title}", back=lambda e: self.page.run_task(self.p_leave)), self.p_list,
                          self.p_status, ft.Container(rec, padding=ft.Padding.only(bottom=18))],
                         spacing=8, expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    async def p_toggle(self):
        if self.p_running:
            return await self.p_stop()
        song = self.nb.song(self.song_id)
        self.p_running, self.p_line = True, -1
        self.p_path = os.path.join(self.takes_dir(), f"toma_{song.id}_{int(time.time())}.m4a")
        self.p_recording = await self.start_recording(self.p_path)
        self.p_t0 = time.monotonic()

        async def on_beat(n):
            if not self.p_running:
                return
            self.p_dot.bgcolor = "#3D0712" if n % 2 else REC
            if n <= 4:
                self.p_status.value = "Cuenta: " + " ".join(str(i) for i in range(1, n + 1)) if n < 4 else "¡Ahora!"
                self.p_status.color = L.accent
                self.page.update()
                if n < 4:
                    return
            if n % 4 == 0:
                self.p_line += 1
                for i, r in enumerate(self.p_rows):
                    r.color = self.L.text if i == self.p_line else self.L.muted
                    r.weight = ft.FontWeight.BOLD if i == self.p_line else None
                if self.p_line < len(self.p_rows):
                    self.p_status.value = f"Barra {self.p_line + 1} de {len(self.p_rows)}" + ("  ·  REC" if self.p_recording else "")
                    await self.p_list.scroll_to(offset=max(0, self.p_line * 52 - 80), duration=300)
                else:
                    self.page.update()
                    return await self.p_stop()
            self.page.update()
        L = self.L
        if song.beat:
            await self.play_beat(song.beat, song.bpm, on_beat)
        else:
            self.metronome_task = asyncio.create_task(self.metronome(song.bpm, on_beat))

    async def p_stop(self, save=True):
        if not self.p_running:
            return
        self.p_running = False
        await self.stop_beat()
        if self.metronome_task:
            self.metronome_task.cancel()
        if self.p_recording:
            path = await self.recorder.stop_recording()
            dur = time.monotonic() - self.p_t0
            if save and path:
                n = len(self.nb.takes(self.song_id)) + 1
                self.nb.add_take(path, dur, self.song_id, "", f"Toma {n}")
                self.p_status.value = f"Toma {n} guardada ({fmt_time(dur)})"
        else:
            self.p_status.value = "Listo"
        self.p_status.color = self.L.muted
        self.page.update()

    async def p_leave(self):
        await self.p_stop()
        self.go("song")

    # ================= aprende: rimas y métrica =================
    def guide_view(self):
        L = self.L
        cards = [ft.Container(ft.Column([
            self.marker("Aprende", 26),
            self.txt("Tipos de rima, métrica y cómo escribir pensando en el beat. Cada lección trae ejemplos y algunas un "
                     "laboratorio para practicar con tus propias palabras.", 13, L.muted)], spacing=4),
            padding=ft.Padding.only(left=4, top=4, right=4, bottom=8))]
        for i, les in enumerate(guide.LESSONS):
            num = ft.Container(self.txt(str(i + 1), 15, L.on_accent, "PoppinsBold"), width=34, height=34, border_radius=34,
                               bgcolor=L.accent, alignment=ft.Alignment.CENTER)
            lab = ft.Container(self.txt("laboratorio", 10, L.accent, "PoppinsSemi"), border_radius=8, bgcolor=W(.14, L.accent),
                               padding=ft.Padding.symmetric(vertical=2, horizontal=8), visible=bool(les["tool"]))
            cards.append(self.card(ft.Row([num, ft.Column([self.txt(les["title"], 16, font="PoppinsSemi"),
                                                           ft.Row([self.txt(les["subtitle"], 12, L.muted), lab], spacing=8)],
                                                          spacing=2, expand=True)], spacing=14),
                                   on_click=lambda e, i=i: self.go("lesson", lesson=i), padding=14))
        return ft.Column([self.header("Rimas y métrica", back=lambda e: self.go("home")),
                          ft.ListView(cards, spacing=10, padding=ft.Padding.only(left=16, top=4, right=16, bottom=20), expand=True)],
                         spacing=0, expand=True)

    def example_line(self, ex):
        L = self.L
        spans = [ft.TextSpan(t, ft.TextStyle(color=L.accent, weight=ft.FontWeight.BOLD) if hi else None)
                 for t, hi in guide.parts(ex)]
        return ft.Container(ft.Text(spans=spans, font_family="Mono", size=15, color=L.text),
                            padding=ft.Padding.symmetric(vertical=10, horizontal=14), border_radius=14,
                            bgcolor=W(.9, L.surface2), border=ft.Border.all(1, W(.6, L.line)))

    def lesson_view(self):
        L = self.L
        i = self.lesson or 0
        les = guide.LESSONS[i]
        body = [self.marker(les["title"], 26), self.txt(les["subtitle"], 14, L.muted)]
        body += [self.txt(p, 15, L.text) for p in les["body"]]
        body.append(self.marker("Ejemplos", 18))
        body += [self.example_line(ex) for ex in les["examples"]]
        if les["tool"] == "rima":
            body += [self.marker("Laboratorio", 18), self.rhyme_lab()]
        elif les["tool"] == "metrica":
            body += [self.marker("Laboratorio", 18), self.meter_lab()]
        nav = []
        if i > 0:
            nav.append(self.button("Anterior", lambda e: self.go("lesson", lesson=i - 1), primary=False, expand=True, height=44))
        if i + 1 < len(guide.LESSONS):
            nav.append(self.button("Siguiente", lambda e: self.go("lesson", lesson=i + 1), expand=True, height=44))
        body.append(ft.Container(ft.Row(nav, spacing=10), padding=ft.Padding.only(top=10)))
        return ft.Column([self.header(f"Lección {i + 1} de {len(guide.LESSONS)}", back=lambda e: self.go("guide")),
                          ft.ListView(body, spacing=12, padding=ft.Padding.only(left=20, top=4, right=20, bottom=24), expand=True)],
                         spacing=0, expand=True)

    def rhyme_lab(self):
        """Escribe una palabra: muestra su tónica, tipo de acento y rimas de cada tipo."""
        L = self.L
        out = ft.Column(spacing=10)
        f = self.field("Escribe una palabra", "camino")

        def run(e=None):
            w = last_word(f.value or "")
            out.controls.clear()
            info = stress_info(w) if w else None
            if not info:
                out.controls.append(self.txt("Escribe una palabra con vocales.", 13, L.muted))
            else:
                idx, kind, lw = info
                out.controls.append(ft.Text(spans=[ft.TextSpan(lw[:idx]),
                                                   ft.TextSpan(lw[idx], ft.TextStyle(color=L.accent, weight=ft.FontWeight.BOLD,
                                                                                     size=26)),
                                                   ft.TextSpan(lw[idx + 1:])], size=22, font_family="Mono", color=L.text))
                out.controls.append(self.txt(f"Vocal tónica resaltada · palabra {kind} · rima desde «{lw[idx:]}»", 12, L.muted))
                for k, name in TYPES.items():
                    found = self.rhymes.find(w, k, 14)
                    out.controls.append(ft.Column([
                        self.txt(name, 13, L.accent, "PoppinsSemi"),
                        ft.Row([ft.Container(self.txt(x, 13, L.text, "Mono"), padding=ft.Padding.symmetric(vertical=4, horizontal=10),
                                             border_radius=10, bgcolor=W(.9, L.surface2)) for x in found] or
                               [self.txt("sin resultados", 12, L.muted)], wrap=True, spacing=6, run_spacing=6)], spacing=4))
            safe_update(out)
        f.on_change = run
        run()
        return self.card(ft.Column([f, out], spacing=12), padding=14)

    def meter_lab(self):
        """Escribe una barra: sílabas, sinalefas, acento final y cuánto ocupa en el compás."""
        L = self.L
        out = ft.Column(spacing=8)
        f = self.field("Escribe una barra", "Antes del beat, nace la idea", mono=True)

        def run(e=None):
            t = f.value or ""
            out.controls.clear()
            if t.strip():
                spans = []
                for w, joins in sinalefas(t):
                    spans.append(ft.TextSpan(w))
                    spans.append(ft.TextSpan("_" if joins else " ", ft.TextStyle(color=L.accent, weight=ft.FontWeight.BOLD)))
                out.controls.append(ft.Text(spans=spans, font_family="Mono", size=17, color=L.text))
                n, sung = count_line(t), count_line_sung(t)
                lw = last_word(t)
                info = stress_info(lw) if lw else None
                stats = [("Sílabas", str(n)), ("Al rapear", str(sung)), ("Final", info[1] if info else "—")]
                out.controls.append(ft.Row([ft.Container(ft.Column([self.txt(v, 20, L.accent, "PoppinsBold"),
                                                                     self.txt(k, 11, L.muted)], spacing=0,
                                                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                                         expand=True, padding=10, border_radius=14, bgcolor=W(.9, L.surface2))
                                            for k, v in stats], spacing=8))
                fit = ("cabe cómoda en corcheas (≤ 8)" if sung <= 8 else
                       "cabe en semicorcheas (≤ 16)" if sung <= 16 else "más de 16: necesitas doble tiempo o dividirla en 2 barras")
                out.controls.append(self.txt(f"_ = sinalefa · En un compás de 4/4: {fit}.", 12, L.muted))
            safe_update(out)
        f.on_change = run
        run()
        return self.card(ft.Column([f, out], spacing=12), padding=14)

    def check_quota(self):
        """Consulta el saldo de Openverse (real) y valida Jamendo (con conteo propio)."""
        L = self.L
        ov = self.txt("Openverse: consultando…", 14)
        jm = self.txt("Jamendo: consultando…", 14)
        jd, jmon = self.nb.requests_used("Jamendo")
        od, _ = self.nb.requests_used("Openverse")

        def ov_done(r, err):
            ov.value = (f"Openverse: {r['day']} de {r['day_limit']} búsquedas disponibles hoy "
                        f"({r['minute']} en este minuto). Hoy hiciste {od}." if r else f"Openverse: {err}")
            safe_update(ov)

        def jm_done(r, err):
            if r:
                jm.value = (f"Jamendo: tu clave funciona. Jamendo no informa el saldo exacto; hoy hiciste {jd} búsquedas "
                            f"y {jmon} este mes (el plan gratis permite aprox. 35.000 al mes).")
            else:
                jm.value = f"Jamendo: {err}"
            safe_update(jm)
        self.dialog("Consultas disponibles", ft.Column([ov, jm], tight=True, spacing=12), [("Cerrar", None)])
        discover.quota("Openverse", "", ov_done)
        discover.quota("Jamendo", self.nb.get_setting("jamendo_client_id"), jm_done)

    # ================= ajustes =================
    def open_settings(self):
        L = self.L

        def chooser(title, options, current, key):
            return ft.Column([self.txt(title, 13, L.muted),
                              ft.Row([self.chip(o, o == current, lambda e, o=o: set_look(key, o), True) for o in options],
                                     wrap=True, spacing=6, run_spacing=6)], spacing=6)

        def set_look(key, value):
            self.nb.set_setting(key, value)
            self.L.set(**{{"theme": "theme", "accent": "accent", "texture": "texture"}[key]: value})
            self.page.pop_dialog()
            self.render()
            self.open_settings()
        jid = self.field("Client ID de Jamendo (para Descubrir bases)", self.nb.get_setting("jamendo_client_id"))
        jid.on_change = lambda e: self.nb.set_setting("jamendo_client_id", (jid.value or "").strip())

        async def export(e):
            name = f"compaszero-{time.strftime('%Y%m%d-%H%M')}.json"
            path = await self.files.save_file(dialog_title="Guardar copia", file_name=name,
                                              src_bytes=self.nb.export_json().encode("utf-8"))
            if path and not os.path.exists(path):  # escritorio: guardar nosotros
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.nb.export_json())
            self.snack("Copia guardada" if path else "Cancelado")

        async def restore(e):
            files = await self.files.pick_files(dialog_title="Elige la copia", file_type=ft.FilePickerFileType.CUSTOM,
                                                allowed_extensions=["json"], with_data=True)
            if not files:
                return
            f = files[0]
            data = f.bytes if getattr(f, "bytes", None) else open(f.path, "rb").read()
            try:
                self.nb.import_json(data.decode("utf-8"))
            except Exception as ex:
                return self.snack(f"No se pudo restaurar: {ex}")
            self.speller.personal = self.nb.personal_words()
            self.page.pop_dialog()
            self.go("home")
            self.snack("Cuaderno restaurado")
        words_ = sorted(self.nb.personal_words())
        content = ft.Column([
            ft.Row([ft.Image(src=L.icon("gear"), width=28, height=28), self.txt("Ajustes", 20, font="PoppinsSemi")], spacing=10),
            chooser("Tema", list(THEMES), L.theme, "theme"),
            chooser("Color de botones y destacados", list(ACCENTS), L.accent_name, "accent"),
            chooser("Fondo", TEXTURES, L.texture, "texture"),
            jid,
            self.button("Ver consultas que me quedan hoy", lambda e: self.check_quota(), primary=False, height=44),
            ft.Row([self.button("Guardar copia", export, primary=False, expand=True, height=44),
                    self.button("Restaurar", restore, primary=False, expand=True, height=44)], spacing=8),
            self.txt("La copia incluye canciones, ideas, freestyles, tu diccionario y tus ajustes (también el client ID). "
                     "No incluye los audios. Puedes guardarla en Google Drive.",
                     11, L.muted),
            self.txt(f"Mi diccionario: {', '.join(words_) if words_ else '(vacío)'}", 12, L.muted)], spacing=14, tight=True)
        self.sheet(content)


async def main(page: ft.Page):
    page.title = "CompásZero"
    app = App(page)
    page.on_view_pop = None

    def back(e):
        if app.screen == "lesson":
            return app.go("guide")
        if app.screen in ("song", "freestyle", "review", "discover", "prompter", "guide"):
            app.go("home" if app.screen != "prompter" else "song")
    page.on_keyboard_event = lambda e: back(e) if e.key == "Escape" else None
    demo = os.getenv("CZ_DEMO")
    if demo:  # capturas de prueba: datos de ejemplo y pantalla directa
        nb = app.nb
        if not nb.songs():
            sid = nb.create_song("Calle de noche")
            for t, sec in [("Camino solo por la calle de noche", "Verso"), ("Con el corazon latiendo en un coche", "Verso"),
                           ("Las luces del barrio me cuentan la historia", "Verso"), ("Y cada esquina guarda una memoria", "Verso"),
                           ("Antes del beat nace la idea", "Coro")]:
                nb.add_bar(t, sid, sec)
            nb.set_song(sid, status="En progreso", tags="#barrio #noche", beat=beats.list_beats(app.data_dir)[0][1])
            nb.add_bar("Una idea suelta que rima con la luna")
            ss = nb.start_session("Boom bap 90 BPM")
            nb.add_line(ss, 2.1, "antes del beat nace la idea")
            nb.add_line(ss, 5.4, "rimo con el alma sin pedir permiso")
            nb.end_session(ss, 42)
        app.song_id = nb.songs()[0].id
        app.session_id = nb.sessions()[0].id
        screen, _, tab = demo.partition(":")
        app.screen, app.tab = screen, int(tab or 0)
        if screen == "lesson":
            app.lesson, app.tab = int(tab or 0), 0
        if screen == "song":
            app.rhyme_kind = "consonante"
    app.render()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
