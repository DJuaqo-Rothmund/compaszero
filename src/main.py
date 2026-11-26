"""CompásZero — cuaderno de rimas para rap (Kivy). Antes del beat, nace la idea."""
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ColorProperty, NumericProperty, StringProperty
from kivy.animation import Animation
from kivy.core.audio import SoundLoader
from kivy.uix.widget import Widget
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.stacklayout import StackLayout
from kivy.factory import Factory

from cz.db import SECTIONS, Bar, Line, Notebook
from cz import beats, speech, discover
from cz.syllables import count_line, count_line_sung, words as Syllables_words
from cz.spelling import Speller, Thesaurus
from cz.rhymes import keys as rhyme_keys
from cz import inspiration, recorder, android_io
from cz.db import STATUSES
import re
from cz.rhymes import TYPES, RhymeIndex, last_word
from cz.theme import C, MONO, icon

HERE = os.path.dirname(os.path.abspath(__file__))
INTRO_SECONDS = 6.0


def _style_copy_paste():
    """Menú de cortar/copiar/pegar de los campos de texto: en español y con el estilo oscuro de Android."""
    from kivy.uix.textinput import TextInputCutCopyPaste
    original = TextInputCutCopyPaste.__init__

    def init(self, **kw):
        original(self, **kw)
        self.background_color = (0.16, 0.16, 0.16, 1)
        self.border = (0, 0, 0, 0)
        try:
            self.content.background_color = (0.16, 0.16, 0.16, 1)
        except Exception:
            pass
        for btn, text in ((self.but_cut, "Cortar"), (self.but_copy, "Copiar"),
                          (self.but_paste, "Pegar"), (self.but_selectall, "Todo")):
            btn.text = text
            btn.background_normal = ""
            btn.background_down = ""
            btn.background_color = (0.16, 0.16, 0.16, 1)
            btn.color = C.chalk
            btn.font_size = "15sp"
    TextInputCutCopyPaste.__init__ = init


_style_copy_paste()


# ---------- widgets ----------

class NavItem(ButtonBehavior, BoxLayout):
    active = BooleanProperty(False)
    name = StringProperty()
    icon_name = StringProperty()


class Card(ButtonBehavior, BoxLayout):
    title = StringProperty()
    subtitle = StringProperty()


RHYME_COLORS = ["E5194B", "F5A623", "4FC3F7", "9CCC65", "BA68C8", "FFD54F", "4DB6AC", "F48FB1"]


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;")


def decorate(text: str, rhyme_color: str | None = None) -> str:
    """Marca en el texto las palabras dudosas (subrayado salmón) y colorea la palabra final según su rima."""
    app = App.get_running_app()
    tokens = re.split(r"([^\W\d_]+)", text)
    last = max((i for i, t in enumerate(tokens) if i % 2 == 1), default=None)
    out = []
    for i, t in enumerate(tokens):
        if i % 2 == 0:
            out.append(esc(t))
        elif i == last and rhyme_color:
            out.append(f"[color={rhyme_color}][b]{esc(t)}[/b][/color]")
        elif app and not app.speller.known(t):
            out.append(f"[color=FF8A80][u]{esc(t)}[/u][/color]")
        else:
            out.append(esc(t))
    return "".join(out)


def rhyme_colors(bars) -> dict:
    """Asigna un color a cada barra cuyo final rima (asonante) con otra barra."""
    groups = {}
    for b in bars:
        k = rhyme_keys(last_word(b.text) or "")
        if k and k["asonante"]:
            groups.setdefault(k["asonante"], []).append(b.id)
    colors, n = {}, 0
    for key, ids in groups.items():
        if len(ids) >= 2:
            for i in ids:
                colors[i] = RHYME_COLORS[n % len(RHYME_COLORS)]
            n += 1
    return colors


class BarRow(ButtonBehavior, BoxLayout):
    text = StringProperty()
    syllables = NumericProperty(0)

    def __init__(self, bar: Bar, on_pick, color=None, **kw):
        super().__init__(text=decorate(bar.text, color), syllables=count_line_sung(bar.text), **kw)
        self.bar = bar
        self.bind(on_release=lambda *_: on_pick(bar))


class Composer(BoxLayout):
    """Escritura rápida: Enter guarda y deja el campo listo para la siguiente barra.

    Modo rimas: al elegir un tipo (consonante, asonante, multisilábica) sugiere palabras
    que riman con la última palabra escrita o, si el campo está vacío, con el final de la
    barra anterior (`context`). Tocar una sugerencia la agrega al texto.
    """
    hint = StringProperty()
    count = StringProperty()
    listening = BooleanProperty(False)

    def __init__(self, hint, on_save, context=lambda: "", **kw):
        super().__init__(hint=hint, **kw)
        self.on_save, self.context = on_save, context
        self._ev = None
        app = App.get_running_app()
        group = f"rk{id(self)}"
        lbl = Label(text="Rimas:", color=C.muted, font_size="13sp", size_hint=(None, None), size=(dp(52), dp(34)))
        self.ids.kinds.add_widget(lbl)
        for kind, name in TYPES.items():
            c = Factory.Chip(text=name, group=group, allow_no_selection=True,
                             state="down" if app.rhyme_kind == kind else "normal")
            c.bind(on_release=lambda w, kind=kind: self.pick_kind(kind if w.state == "down" else None))
            self.ids.kinds.add_widget(c)
        Clock.schedule_once(lambda dt: self.show_rhymes())

    def pick_kind(self, kind):
        App.get_running_app().rhyme_kind = kind
        self.show_rhymes()

    def on_field(self, text):
        self.count = syllable_text(text) if text.strip() else ""
        if self._ev:
            self._ev.cancel()
        self._ev = Clock.schedule_once(lambda dt: self.show_rhymes(), 0.35)

    def show_rhymes(self):
        app = App.get_running_app()
        box, row = self.ids.rhyme_box, self.ids.rhymes
        kind = app.rhyme_kind
        target = last_word(self.ids.field.text) or last_word(self.context())
        row.clear_widgets()
        if not kind:
            box.height, box.opacity = 0, 0
            return
        box.height, box.opacity = dp(56), 1
        if not target:
            self.ids.rhyme_title.text = "Escribe una palabra para ver rimas"
            return
        words = app.rhymes.find(target, kind, limit=40)
        self.ids.rhyme_title.text = (f"{TYPES[kind]} con «{target}»" if words
                                     else f"Sin rimas {TYPES[kind].lower()}s para «{target}»")
        for w in words:
            b = Factory.RhymeWord(text=w)
            b.bind(on_release=lambda btn, w=w: self.insert(w))
            row.add_widget(b)

    def dictate(self):
        """Dictar una barra con la voz (reconocedor de Android); el texto queda para corregir."""
        if self.listening:
            self._dict.stop()
            self.listening = False
            return
        if not speech.available():
            return App.get_running_app().toast("El dictado solo funciona en el teléfono")

        def final(text):
            self._dict.stop()
            self.listening = False
            f = self.ids.field
            f.text = (f.text.rstrip() + " " + text).strip()
            f.focus = True

        def go(ok):
            if not ok:
                return
            self._dict = speech.listener(lambda t: setattr(self, "count", t), final,
                                         lambda m: (setattr(self, "listening", False), setattr(self, "count", m)))
            self._dict.start()
            self.listening = True
        speech.ask_mic_permission(go)

    def insert(self, word):
        f = self.ids.field
        f.text = (f.text.rstrip() + " " + word).lstrip() + " "
        f.cursor = (len(f.text), 0)
        f.focus = True

    def submit(self):
        f = self.ids.field
        if f.text.strip():
            self.on_save(f.text)
            f.text = ""
            Clock.schedule_once(lambda dt: setattr(f, "focus", True), 0.05)


def scroll_list(widgets, spacing=dp(8)) -> ScrollView:
    box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=spacing, padding=dp(16))
    box.bind(minimum_height=box.setter("height"))
    for w in widgets:
        box.add_widget(w)
    sv = ScrollView(do_scroll_x=False)
    sv.add_widget(box)
    return sv


def empty(text) -> Label:
    return Label(text=text, color=C.muted, halign="center", font_size="15sp")


def chips(selected, on_pick) -> StackLayout:
    row = StackLayout(size_hint_y=None, spacing=dp(6), padding=(dp(12), dp(6)))
    row.bind(minimum_height=row.setter("height"))
    group = f"sec{id(row)}"
    for s in SECTIONS:
        c = Factory.Chip(text=s, group=group, state="down" if s == selected else "normal")
        c.bind(on_release=lambda w, s=s: on_pick(s))
        row.add_widget(c)
    return row


def brand_title():
    """Logo grafiti «Compás Zero»."""
    return Image(source=os.path.join(HERE, "assets", "wordmark.png"), fit_mode="contain",
                 size_hint=(None, None), size=(dp(120), dp(52)), pos_hint={"center_y": .5})


def icon_button(name, cb, size=44):
    b = Factory.IconButton(source=icon(name), size=(dp(size), dp(size)), pos_hint={"center_y": .5})
    b.bind(on_release=lambda *_: cb())
    return b


def dialog(title, body, actions) -> ModalView:
    """Diálogo simple: título, contenido y botones [(texto, callback, es_peligroso)]."""
    mv = ModalView(size_hint=(.9, None), background_color=(0, 0, 0, .7), background="")
    box = Factory.Surface(orientation="vertical", padding=dp(16), spacing=dp(12), size_hint_y=None)
    box.bind(minimum_height=box.setter("height"))
    box.add_widget(Label(text=title, bold=True, font_size="18sp", size_hint_y=None, height=dp(30),
                         halign="left", text_size=(Window.width * .8, None)))
    sv = ScrollView(do_scroll_x=False, size_hint_y=None)
    sv.add_widget(body)
    body.bind(height=lambda w, h: setattr(sv, "height", min(h, Window.height * .62)))
    sv.height = min(body.height, Window.height * .62)
    box.add_widget(sv)
    row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    row.add_widget(Label())
    for text, cb, danger in actions:
        b = Factory.FlatButton(text=text, size_hint_x=None, width=dp(84),
                               color=C.rec if danger else C.chalk, bold=True)
        b.bind(on_release=lambda w, cb=cb: (mv.dismiss(), cb()))
        row.add_widget(b)
    box.add_widget(row)
    mv.add_widget(box)
    mv.bind(height=lambda *_: None)
    box.bind(height=lambda w, h: setattr(mv, "height", h))
    mv.open()
    return mv


def text_input(value="", hint="", lyric=True, multiline=False):
    t = Factory.LyricInput(text=value, hint_text=hint, multiline=multiline, size_hint_y=None,
                           height=dp(96) if multiline else dp(48))
    if not lyric:
        t.font_name = "Roboto"
    return t


def syllable_text(text: str) -> str:
    return f"{count_line(text)} sílabas · {count_line_sung(text)} al rapear"


def lyric_editor(value):
    """Editor de una barra: texto, sílabas, ortografía (sugerencias / diccionario) y sinónimos."""
    app = App.get_running_app()
    box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
    box.bind(minimum_height=box.setter("height"))
    t = text_input(value, multiline=True)
    n = Label(text=syllable_text(value), color=C.muted, font_size="12sp", size_hint_y=None, height=dp(18), halign="left")
    n.bind(size=lambda w, s: setattr(w, "text_size", s))
    words_row = StackLayout(size_hint_y=None, spacing=dp(6))
    words_row.bind(minimum_height=words_row.setter("height"))
    panel = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
    panel.bind(minimum_height=panel.setter("height"))

    def replace(old, new):
        t.text = re.sub(rf"\b{re.escape(old)}\b", new, t.text, count=1)

    def show_word(w):
        panel.clear_widgets()
        options = []
        if not app.speller.known(w):
            panel.add_widget(Label(text=f"«{w}» no está en el diccionario", color=(1, .54, .5, 1), font_size="13sp",
                                   size_hint_y=None, height=dp(20)))
            options = [(x, x) for x in app.speller.suggest(w)]
            add = Factory.FlatButton(text="+ Agregar a mi diccionario", font_size="13sp", size_hint_y=None, height=dp(32))
            add.bind(on_release=lambda *_: (app.nb.add_word(w), app.speller.personal.add(w.lower()), refresh()))
            panel.add_widget(add)
        syn = app.thesaurus.synonyms(w)
        if syn:
            panel.add_widget(Label(text=f"Sinónimos de «{w}»", color=C.muted, font_size="12sp", size_hint_y=None, height=dp(18)))
        options += [(x, x) for x in syn[:18]]
        if not options and app.speller.known(w):
            panel.add_widget(Label(text=f"Sin sinónimos para «{w}»", color=C.muted, font_size="12sp", size_hint_y=None, height=dp(18)))
        row = StackLayout(size_hint_y=None, spacing=dp(6))
        row.bind(minimum_height=row.setter("height"))
        for label, val in options:
            b = Factory.RhymeWord(text=label, size_hint_y=None, height=dp(32))
            b.bind(on_release=lambda btn, val=val: (replace(w, val), refresh()))
            row.add_widget(b)
        panel.add_widget(row)

    def refresh(*_):
        n.text = syllable_text(t.text)
        words_row.clear_widgets()
        panel.clear_widgets()
        seen = []
        for w in Syllables_words(t.text):
            if w in seen or len(seen) >= 14:
                continue
            seen.append(w)
            bad = not app.speller.known(w)
            c = Factory.Chip(text=w, group=f"w{id(box)}", allow_no_selection=True,
                             color=(1, .54, .5, 1) if bad else C.chalk)
            c.bind(on_release=lambda btn, w=w: show_word(w) if btn.state == "down" else panel.clear_widgets())
            words_row.add_widget(c)

    ev = {}
    t.bind(text=lambda *_: (ev.get("e") and ev["e"].cancel(), ev.update(e=Clock.schedule_once(refresh, .4))))
    box.add_widget(t); box.add_widget(n)
    box.add_widget(Label(text="Toca una palabra: sinónimos y ortografía", color=C.muted, font_size="12sp",
                         size_hint_y=None, height=dp(18), halign="left", text_size=(Window.width * .8, None)))
    box.add_widget(words_row); box.add_widget(panel)
    refresh()
    return t, box


# ---------- pantallas ----------

class IntroScreen(Screen):
    def on_enter(self):
        # los cuadros se cargan primero; el tiempo cuenta desde que empieza a reproducirse
        self._ev = Clock.schedule_once(lambda dt: self.finish(), INTRO_SECONDS + 4)  # tope de seguridad
        img = Image(source=os.path.join(HERE, "assets", "intro.zip"), anim_delay=0.04, anim_loop=1,
                    fit_mode="contain")
        self.add_widget(img)

        def started(*_):
            self._ev.cancel()
            self._ev = Clock.schedule_once(lambda dt: self.finish(), INTRO_SECONDS)
        if img.texture:
            started()
        else:
            img.bind(texture=lambda *a: started() if not getattr(self, "_started", False) and not setattr(self, "_started", True) else None)

    def on_touch_down(self, touch):  # tocar salta la intro
        self.finish()
        return True

    def finish(self):
        if self.manager.current == "intro":
            self._ev.cancel()
            self.manager.current = "home"


class HomeScreen(Screen):
    tab = 0
    query = ""
    _search_ev = None

    def on_search(self, v):
        self.query = v
        if self._search_ev:
            self._search_ev.cancel()
        self._search_ev = Clock.schedule_once(lambda dt: self._refresh_list(), .4)

    def _refresh_list(self):
        self.render()
        # mantener el foco en el buscador
        for w in self.walk():
            if getattr(w, "hint_text", "").startswith("Buscar"):
                w.focus = True
                w.cursor = (len(w.text), 0)

    def _challenge(self):
        """Reto del día: tema + palabra obligatoria, y la racha de días escribiendo."""
        app = App.get_running_app()
        if not hasattr(self, "_theme"):
            self._theme, self._word = inspiration.daily()
        streak = app.nb.streak()
        box = Factory.Surface(orientation="vertical", size_hint_y=None, height=dp(138), padding=dp(14), spacing=dp(4))
        head = Label(text=f"[b]RETO DEL DÍA[/b]   [color=8A8A8A]racha: {streak} {'día' if streak == 1 else 'días'}[/color]",
                     markup=True, color=C.rec, font_size="13sp", size_hint_y=None, height=dp(20), halign="left")
        theme = Label(text=self._theme, bold=True, font_size="17sp", size_hint_y=None, height=dp(26), halign="left")
        word = Label(text=f"Usa la palabra: [b]{self._word}[/b]", markup=True, color=C.muted, font_size="14sp",
                     size_hint_y=None, height=dp(22), halign="left")
        for l in (head, theme, word):
            l.bind(size=lambda w, sz: setattr(w, "text_size", sz))
            box.add_widget(l)
        row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        go = Factory.RecButton(text="Escribir", font_size="14sp")
        go.bind(on_release=lambda *_: app.start_challenge(self._theme, self._word))
        other = Factory.FlatButton(text="Otro tema", font_size="14sp")
        other.bind(on_release=lambda *_: (setattr(self, "_theme", inspiration.random_theme()),
                                          setattr(self, "_word", inspiration.random_word(self._word)), self.render()))
        row.add_widget(go); row.add_widget(other)
        box.add_widget(row)
        return box

    def on_pre_enter(self):
        self.render()

    def render(self):
        app = App.get_running_app()
        self.clear_widgets()
        root = BoxLayout(orientation="vertical")
        top = Factory.TopBar()
        top.height = dp(64)
        top.add_widget(Widget(size_hint_x=None, width=dp(44))); top.add_widget(Widget()); top.add_widget(brand_title())
        top.add_widget(Widget()); top.add_widget(icon_button("gear", app.settings))
        root.add_widget(top)

        layer = FloatLayout()
        if self.tab == 0:
            col = BoxLayout(orientation="vertical")
            search = Factory.LyricInput(text=self.query, hint_text="Buscar en títulos, letras y #etiquetas",
                                        font_name="Roboto", multiline=False, size_hint_y=None, height=dp(46))
            search.bind(text=lambda w, v: self.on_search(v))
            wrap = BoxLayout(size_hint_y=None, height=dp(56), padding=(dp(12), dp(5)))
            wrap.add_widget(search)
            col.add_widget(wrap)
            songs = app.nb.search(self.query) if self.query.strip() else app.nb.songs()
            cards = ([] if self.query.strip() else [self._challenge()]) + [self._card(s) for s in songs]
            if self.query.strip() and not songs:
                col.add_widget(empty("Nada encontrado."))
            else:
                col.add_widget(scroll_list(cards, spacing=dp(10)))
            layer.add_widget(col)
            fab = Factory.RoundIcon(source=icon("plus"), size_hint=(None, None), size=(dp(60), dp(60)),
                                    pos_hint={"right": .94, "y": .03})
            fab.bind(on_release=lambda *_: app.new_song())
            layer.add_widget(fab)
            root.add_widget(layer)
        elif self.tab == 2:
            sessions = app.nb.sessions()
            body = (empty("Elige una base, rapea y la app\nte transcribe lo que dices.") if not sessions else
                    scroll_list([self._session_card(x) for x in sessions], spacing=dp(10)))
            layer.add_widget(body)
            root.add_widget(layer)
            go = Factory.RecButton(text="Empezar freestyle", font_size="17sp", size_hint=(1, None), height=dp(56))
            go.bind(on_release=lambda *_: app.open_freestyle())
            wrap = BoxLayout(size_hint_y=None, height=dp(72), padding=(dp(16), dp(8)))
            wrap.add_widget(go)
            root.add_widget(wrap)
        else:
            ideas = app.nb.ideas()
            notes = app.nb.voice_notes()
            rec_on = app.recorder.recording
            vbtn = Factory.RecButton(text="Detener nota de voz" if rec_on else "Grabar nota de voz", font_size="14sp",
                                     size_hint_y=None, height=dp(44))
            vbtn.bind(on_release=lambda *_: app.toggle_voice_note(self.render))
            vwrap = BoxLayout(size_hint_y=None, height=dp(56), padding=(dp(12), dp(6)))
            vwrap.add_widget(vbtn)
            items = [app.take_row(n, self.render) for n in notes] + [BarRow(b, app.idea_actions) for b in ideas]
            col = BoxLayout(orientation="vertical")
            col.add_widget(vwrap)
            col.add_widget(empty("Anota frases sueltas aquí o graba una nota de voz.\nLuego muévelas a una canción.")
                           if not items else scroll_list(items))
            layer.add_widget(col)
            root.add_widget(layer)
            root.add_widget(Composer("Escribe una barra…", lambda t: (app.nb.add_bar(t), self.render()),
                                     context=lambda: ideas[0].text if ideas else ""))

        nav = BoxLayout(size_hint_y=None, height=dp(68))
        for i, (name, ic) in enumerate([("Canciones", "canciones"), ("Ideas", "ideas"), ("Freestyle", "freestyle")]):
            b = NavItem(name=name, icon_name=ic, active=self.tab == i)
            b.bind(on_release=lambda w, i=i: self.switch(i))
            nav.add_widget(b)
        with nav.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*C.graphite)
            r = Rectangle()
        nav.bind(pos=lambda w, p: setattr(r, "pos", p), size=lambda w, s: setattr(r, "size", s))
        root.add_widget(nav)
        self.add_widget(root)

    def _card(self, s):
        c = Card(title=s.title, subtitle=f"{s.status} · {s.bars} barras" + (f" · {s.tags}" if s.tags else ""))
        c.bind(on_release=lambda *_: App.get_running_app().open_song(s.id))
        return c

    def _session_card(self, x):
        when = time.strftime("%d/%m %H:%M", time.localtime(x.created_at))
        c = Card(title=f"Freestyle · {x.beat}", subtitle=f"{when} · {x.lines} líneas · {fmt_time(x.duration)}")
        c.bind(on_release=lambda *_: App.get_running_app().open_review(x.id))
        return c

    def switch(self, i):
        self.tab = i
        self.render()


def bpm_of(path_or_name: str, default: int = 90) -> int:
    m = re.search(r"(\d{2,3})\s*bpm", os.path.basename(path_or_name or "").lower())
    return int(m.group(1)) if m else default


class BeatPlayer:
    """Reproduce una base en loop y avisa en cada tiempo (metrónomo visual)."""

    def __init__(self):
        self.sound, self.path, self._ev, self.on_beat = None, None, None, None

    def play(self, path, bpm, on_beat=None):
        self.stop()
        self.sound = SoundLoader.load(path) if path and os.path.exists(path) else None
        self.path, self.on_beat = path, on_beat
        if self.sound:
            self.sound.loop = True
            self.sound.play()
        self.n = 0
        self._ev = Clock.schedule_interval(self._tick, 60.0 / max(bpm, 40))

    def _tick(self, dt):
        self.n += 1
        if self.on_beat:
            self.on_beat(self.n)

    def stop(self):
        if self._ev:
            self._ev.cancel()
            self._ev = None
        if self.sound:
            self.sound.stop()
            self.sound = None
        self.path = None

    @property
    def playing(self):
        return self._ev is not None


class SongScreen(Screen):
    song_id = None
    section = "Verso"

    def on_pre_enter(self):
        self.render()

    def on_leave(self):
        app = App.get_running_app()
        app.beat.stop()
        app.stop_take_playback()
        if self.song_id:
            app.nb.snapshot(self.song_id)  # historial de versiones

    def render(self):
        app = App.get_running_app()
        song = app.nb.song(self.song_id)
        self.clear_widgets()
        if song is None:
            return
        root = BoxLayout(orientation="vertical")
        top = Factory.TopBar()
        back = icon_button("back", app.go_home)
        title = Factory.FlatButton(text=song.title, bold=True, font_size="19sp", halign="left")
        title.bind(size=lambda w, s: setattr(w, "text_size", s), on_release=lambda *_: app.rename(song))
        title.valign = "middle"
        more = icon_button("mas", lambda: app.song_menu(song))
        for w in (back, title, more):
            top.add_widget(w)
        root.add_widget(top)
        root.add_widget(self.beat_strip(song))

        bars = app.nb.bars(song.id)
        colors = rhyme_colors(bars)
        groups: dict[str, list[Bar]] = {}
        for b in bars:
            groups.setdefault(b.section or "Sin sección", []).append(b)
        items = []
        if song.tags or song.status:
            info = Label(text=f"[color=E5194B]{esc(song.status)}[/color]   [color=8A8A8A]{esc(song.tags)}[/color]",
                         markup=True, font_size="13sp", size_hint_y=None, height=dp(20), halign="left")
            info.bind(size=lambda w, s: setattr(w, "text_size", s))
            items.append(info)
        spb = 4 * 60 / max(song.bpm, 40)  # segundos por compás
        for name in SECTIONS + [k for k in groups if k not in SECTIONS]:
            if name in groups:
                n = len(groups[name])
                h = Label(text=f"[b][color=E5194B]{name.upper()}[/color][/b]   [color=8A8A8A][size=12sp]{n} compases ≈ {fmt_time(n * spb)}[/size][/color]",
                          markup=True, size_hint_y=None, height=dp(34), halign="left", valign="bottom")
                h.bind(size=lambda w, s: setattr(w, "text_size", s))
                items.append(h)
                items += [BarRow(b, app.edit_bar, colors.get(b.id)) for b in groups[name]]
        takes = app.nb.takes(song.id)
        if takes:
            h = Label(text="[b][color=E5194B]TOMAS[/color][/b]", markup=True, size_hint_y=None, height=dp(34),
                      halign="left", valign="bottom")
            h.bind(size=lambda w, s: setattr(w, "text_size", s))
            items.append(h)
            items += [app.take_row(tk, self.render) for tk in takes]
        root.add_widget(scroll_list(items, spacing=dp(6)) if items else empty("Escribe la primera barra abajo."))
        root.add_widget(chips(self.section, self.pick))
        root.add_widget(Composer(f"Barra en {self.section}…",
                                 lambda t: (app.nb.add_bar(t, song.id, self.section), self.render()),
                                 context=lambda: bars[-1].text if bars else ""))
        self.add_widget(root)

    def beat_strip(self, song):
        """Base vinculada: reproducir en loop mientras escribes + metrónomo visual (la línea del logo)."""
        app = App.get_running_app()
        strip = BoxLayout(size_hint_y=None, height=dp(44), padding=(dp(12), dp(4)), spacing=dp(8))
        name = os.path.splitext(os.path.basename(song.beat))[0] if song.beat else "Sin base"
        playing = app.beat.playing and app.beat.path == song.beat
        btn = Factory.IconButton(source=icon("stop" if playing else "play"), size=(dp(36), dp(36)), pos_hint={"center_y": .5})
        lbl = Factory.FlatButton(text=f"{name} · {song.bpm} BPM", font_size="14sp", halign="left", color=C.chalk)
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s), on_release=lambda *_: app.pick_song_beat(song))
        lbl.valign = "middle"
        pulse = Widget(size_hint_x=None, width=dp(6))
        from kivy.graphics import Color, Rectangle
        with pulse.canvas:
            col = Color(*C.graphite2)
            rect = Rectangle()
        pulse.bind(pos=lambda w, p: setattr(rect, "pos", p), size=lambda w, sz: setattr(rect, "size", sz))

        def on_beat(n):
            col.rgba = C.rec if n % 4 == 1 else C.chalk  # tiempo 1 de cada compás en rojo
            Animation.cancel_all(col)
            Animation(rgba=C.graphite2, d=.25).start(col)

        def toggle(*_):
            if app.beat.playing and app.beat.path == song.beat:
                app.beat.stop()
            elif not song.beat:
                return app.pick_song_beat(song)
            else:
                app.beat.play(song.beat, song.bpm, on_beat)
            btn.source = icon("stop" if app.beat.playing else "play")
        if playing:
            app.beat.on_beat = on_beat
        btn.bind(on_release=toggle)
        strip.add_widget(btn); strip.add_widget(lbl); strip.add_widget(pulse)
        return strip

    def pick(self, s):
        self.section = s
        self.render()


def fmt_time(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


def top_bar(title, on_back, right=None):
    top = Factory.TopBar()
    back = icon_button("back", on_back)
    t = Label(text=title, bold=True, font_size="19sp", halign="left", valign="middle", shorten=True)
    t.bind(size=lambda w, s: setattr(w, "text_size", s))
    top.add_widget(back); top.add_widget(t)
    if right:
        top.add_widget(right)
    return top


class RecDot(ButtonBehavior, Widget):
    """Botón de grabar: el punto rojo del logo, que late mientras graba."""
    dot = ColorProperty(C.rec)

    def pulse(self, on):
        Animation.cancel_all(self, "dot")
        if on:
            a = Animation(dot=C.rec_off, d=.8, t="in_out_sine") + Animation(dot=C.rec, d=.8, t="in_out_sine")
            a.repeat = True
            a.start(self)
        else:
            self.dot = C.rec


class FreestyleScreen(Screen):
    """Suena la base y el reconocedor de voz transcribe lo que rapeas."""
    beat = None

    def on_pre_enter(self):
        self.running = False
        self.render()

    def render(self):
        app = App.get_running_app()
        self.clear_widgets()
        self.beats = beats.list_beats(app.data_dir)
        if self.beat not in [p for _, p in self.beats]:
            self.beat = self.beats[0][1] if self.beats else None
        root = BoxLayout(orientation="vertical")
        right = BoxLayout(size_hint_x=None, width=dp(96), spacing=dp(4))
        right.add_widget(icon_button("descubrir", lambda: setattr(app.sm, "current", "discover")))
        right.add_widget(icon_button("importar_off", self.import_beat))
        root.add_widget(top_bar("Freestyle", self.leave, right))

        row = StackLayout(size_hint_y=None, spacing=dp(6), padding=(dp(12), dp(4)))
        row.bind(minimum_height=row.setter("height"))
        for name, path in self.beats:
            c = Factory.Chip(text=name[:28], group="beat", state="down" if path == self.beat else "normal")
            c.bind(on_release=lambda w, p=path: (setattr(self, "beat", p), self.show_credit()))
            row.add_widget(c)
        root.add_widget(row)
        self.credit = Label(text="", color=C.muted, font_size="11sp", size_hint_y=None, height=dp(18), halign="left", shorten=True)
        self.credit.bind(size=lambda w, sz: setattr(w, "text_size", (sz[0] - dp(24), sz[1])))
        root.add_widget(self.credit)
        self.show_credit()

        self.lines_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6), padding=dp(16))
        self.lines_box.bind(minimum_height=self.lines_box.setter("height"))
        self.partial = Label(text="", color=C.muted, italic=True, font_name=MONO, size_hint_y=None, halign="left")
        self.partial.bind(width=lambda w, v: setattr(w, "text_size", (v, None)),
                          texture_size=lambda w, s: setattr(w, "height", s[1]))
        self.lines_box.add_widget(self.partial)
        self.scroll = ScrollView(do_scroll_x=False)
        self.scroll.add_widget(self.lines_box)
        root.add_widget(self.scroll)

        wrow = BoxLayout(size_hint_y=None, height=dp(40), padding=(dp(12), 0), spacing=dp(8))
        self.words_on = getattr(self, "words_on", False)
        wt = Factory.Chip(text="Palabras al azar", state="down" if self.words_on else "normal", allow_no_selection=True)
        wt.bind(on_release=lambda w: setattr(self, "words_on", w.state == "down"))
        self.word_lbl = Label(text="", bold=True, font_size="22sp", color=C.rec)
        wrow.add_widget(wt); wrow.add_widget(self.word_lbl)
        root.add_widget(wrow)
        self.hint = Label(text="Usa audífonos: así el micrófono escucha tu voz y no la pista.",
                          color=C.muted, font_size="13sp", size_hint_y=None, height=dp(36), halign="center")
        self.hint.bind(width=lambda w, v: setattr(w, "text_size", (v - dp(24), None)))
        root.add_widget(self.hint)
        bottom = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(150), padding=dp(8), spacing=dp(6))
        self.dot = RecDot(pos_hint={"center_x": .5})
        self.dot.bind(on_release=lambda *_: self.toggle())
        self.clock_lbl = Label(text="Toca para empezar", color=C.muted, size_hint_y=None, height=dp(24))
        bottom.add_widget(self.dot); bottom.add_widget(self.clock_lbl)
        root.add_widget(bottom)
        self.add_widget(root)

    def show_credit(self):
        c = discover.credits_for(self.beat) if self.beat else None
        self.credit.text = (f"  Base: «{c['title']}» de {c['artist']} · {discover.license_label(c['license'])} · {c['source']}"
                            if c else "")

    def import_beat(self):
        try:
            from plyer import filechooser
        except ImportError:
            return self.say("Para importar bases instala plyer.")

        def chosen(sel):
            if sel:
                p = beats.import_beat(App.get_running_app().data_dir, sel[0])
                self.beat = p
                Clock.schedule_once(lambda dt: self.render())
        filechooser.open_file(on_selection=chosen, filters=[["Audio", "*.mp3", "*.wav", "*.ogg", "*.m4a"]])

    def say(self, msg):
        self.clock_lbl.text = msg

    def toggle(self):
        if self.running:
            self.stop()
        else:
            speech.ask_mic_permission(lambda ok: self.start() if ok else self.say("Sin permiso de micrófono"))

    def start(self):
        app = App.get_running_app()
        if not self.beat:
            return self.say("Importa o elige una base")
        if not speech.available():
            return self.say("El dictado solo funciona en el teléfono")
        self.sound = SoundLoader.load(self.beat)
        if self.sound:
            self.sound.loop = True
            self.sound.play()
        name = os.path.splitext(os.path.basename(self.beat))[0]
        self.session = app.nb.start_session(name)
        self.t0 = time.monotonic()
        self.running = True
        self.listener = speech.listener(self.on_partial, self.on_final, self.say)
        self.listener.start()
        self.dot.pulse(True)
        if self.words_on:  # una palabra nueva cada 8 compases
            every = 8 * 4 * 60 / bpm_of(self.beat)
            self.word_lbl.text = inspiration.random_word()
            self._words = Clock.schedule_interval(lambda dt: setattr(self.word_lbl, "text", inspiration.random_word(self.word_lbl.text)), every)
        self.clock_lbl.color = C.rec
        self._tick = Clock.schedule_interval(lambda dt: setattr(self.clock_lbl, "text", f"REC  {fmt_time(time.monotonic() - self.t0)}"), .5)

    def on_partial(self, text):
        if self.running:
            self.partial.text = text

    def on_final(self, text):
        if not self.running or not text.strip():
            return
        t = time.monotonic() - self.t0
        App.get_running_app().nb.add_line(self.session, t, text)
        row = Label(text=f"[color=8A8A8A]{fmt_time(t)}[/color]  {text}", markup=True, font_name=MONO,
                    size_hint_y=None, halign="left")
        row.bind(width=lambda w, v: setattr(w, "text_size", (v, None)), texture_size=lambda w, s: setattr(w, "height", s[1]))
        self.lines_box.add_widget(row, index=1)  # el texto parcial queda siempre abajo
        self.partial.text = ""
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), .05)

    def stop(self, review=True):
        if not self.running:
            return
        self.running = False
        self.listener.stop()
        self._tick.cancel()
        self.dot.pulse(False)
        if getattr(self, "_words", None):
            self._words.cancel()
            self._words = None
        self.word_lbl.text = ""
        self.clock_lbl.color = C.muted
        if getattr(self, "sound", None):
            self.sound.stop()
        app = App.get_running_app()
        app.nb.end_session(self.session, time.monotonic() - self.t0)
        if review:
            app.open_review(self.session)

    def leave(self):
        self.stop(review=False)
        App.get_running_app().go_home()

    def on_leave(self):
        self.stop(review=False)


class ReviewScreen(Screen):
    """Revisión de un freestyle: corrige lo transcrito y pásalo al cuaderno."""
    session_id = None

    def on_pre_enter(self):
        self.render()

    def render(self):
        app = App.get_running_app()
        s = app.nb.session(self.session_id)
        self.clear_widgets()
        if s is None:
            return
        lines = app.nb.lines(s.id)
        delete = Factory.FlatButton(text="Borrar", color=C.rec, size_hint_x=None, width=dp(72))
        delete.bind(on_release=lambda *_: dialog("¿Borrar este freestyle?", Label(size_hint_y=None, height=dp(4)), [
            ("Cancelar", lambda: None, False),
            ("Borrar", lambda: (app.nb.delete_session(s.id), app.go_home()), True)]))
        root = BoxLayout(orientation="vertical")
        root.add_widget(top_bar(f"Revisión · {s.beat}", app.go_home, delete))
        rows = [self._row(l) for l in lines]
        root.add_widget(scroll_list(rows, spacing=dp(6)) if rows else
                        empty("No se transcribió nada.\nPrueba hablar más cerca del micrófono."))
        if lines:
            acts = BoxLayout(size_hint_y=None, height=dp(64), padding=(dp(12), dp(8)), spacing=dp(8))
            a = Factory.FlatButton(text="Todo a ideas")
            a.bind(on_release=lambda *_: self.to_ideas(lines))
            b = Factory.RecButton(text="Nueva canción")
            b.bind(on_release=lambda *_: self.to_song(s, lines))
            acts.add_widget(a); acts.add_widget(b)
            root.add_widget(acts)
        self.add_widget(root)

    def _row(self, line: Line):
        r = BarRow(Bar(line.id, None, "", line.text, 0), lambda b: self.edit(line))
        stamp = Label(text=fmt_time(line.t), color=C.muted, font_name=MONO, font_size="12sp",
                      size_hint_x=None, width=dp(40))
        r.add_widget(stamp, index=len(r.children))
        return r

    def edit(self, line):
        app = App.get_running_app()
        t, box = lyric_editor(line.text)
        dialog(f"Línea en {fmt_time(line.t)}", box, [
            ("Borrar", lambda: (app.nb.delete_line(line.id), self.render()), True),
            ("A ideas", lambda: (app.nb.update_line(line.id, t.text), app.nb.add_bar(t.text), self.render()), False),
            ("Guardar", lambda: (app.nb.update_line(line.id, t.text), self.render()), False)])

    def to_ideas(self, lines):
        app = App.get_running_app()
        for l in lines:
            app.nb.add_bar(l.text)
        self.render()
        dialog("Listo", Label(text=f"{len(lines)} líneas en Ideas sueltas.", size_hint_y=None, height=dp(30)),
               [("OK", lambda: None, False)])

    def to_song(self, s, lines):
        app = App.get_running_app()
        sid = app.nb.create_song(f"Freestyle {time.strftime('%d/%m', time.localtime(s.created_at))}")
        for l in lines:
            app.nb.add_bar(l.text, sid, "Verso")
        app.open_song(sid)


class DiscoverScreen(Screen):
    """Buscar bases libres (Jamendo / Openverse), escucharlas y descargarlas al teléfono."""
    style, source, query, publish_only = "Boom bap", "Openverse", "", False

    def on_pre_enter(self):
        self.results, self.page = [], 1
        self.render()
        self.search()

    def on_leave(self):
        self.stop_preview()

    def render(self):
        self.clear_widgets()
        root = BoxLayout(orientation="vertical")
        root.add_widget(top_bar("Descubrir bases", self.leave))
        bar = BoxLayout(size_hint_y=None, height=dp(54), padding=(dp(12), dp(5)), spacing=dp(8))
        self.q = Factory.LyricInput(text=self.query, hint_text="Buscar (opcional): oscuro, piano, 90s…", font_name="Roboto",
                                    multiline=False)
        self.q.bind(on_text_validate=lambda *_: self.new_search())
        go = Factory.RoundIcon(source=icon("buscar"), size_hint=(None, None), size=(dp(44), dp(44)), pos_hint={"center_y": .5})
        go.bind(on_release=lambda *_: self.new_search())
        bar.add_widget(self.q); bar.add_widget(go)
        root.add_widget(bar)

        def chip_row(options, current, group, cb):
            row = StackLayout(size_hint_y=None, spacing=dp(6), padding=(dp(12), dp(2)))
            row.bind(minimum_height=row.setter("height"))
            for o in options:
                c = Factory.Chip(text=o, group=group, state="down" if o == current else "normal")
                c.bind(on_release=lambda w, o=o: cb(o))
                row.add_widget(c)
            return row
        root.add_widget(chip_row(list(discover.STYLES), self.style, "dstyle", lambda o: self.set_and_search("style", o)))
        src = chip_row(["Openverse", "Jamendo"], self.source, "dsrc", lambda o: self.set_and_search("source", o))
        pub = Factory.Chip(text="Solo para publicar", state="down" if self.publish_only else "normal", allow_no_selection=True)
        pub.bind(on_release=lambda w: self.set_and_search("publish_only", w.state == "down"))
        src.add_widget(pub)
        root.add_widget(src)
        self.status = Label(text="", color=C.muted, font_size="13sp", size_hint_y=None, height=dp(26))
        root.add_widget(self.status)
        self.box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=dp(12))
        self.box.bind(minimum_height=self.box.setter("height"))
        sv = ScrollView(do_scroll_x=False)
        sv.add_widget(self.box)
        root.add_widget(sv)
        note = Label(text="Bases con licencia Creative Commons. Se guarda el autor y la licencia para darle crédito.",
                     color=C.muted, font_size="11sp", size_hint_y=None, height=dp(30), halign="center")
        note.bind(width=lambda w, v: setattr(w, "text_size", (v - dp(20), None)))
        root.add_widget(note)
        self.add_widget(root)
        self.fill()

    def set_and_search(self, attr, value):
        setattr(self, attr, value)
        self.new_search()

    def new_search(self):
        self.query = self.q.text
        self.results, self.page = [], 1
        self.box.clear_widgets()
        self.search()

    def search(self):
        app = App.get_running_app()
        self.status.text = f"Buscando en {self.source}…"
        discover.search(self.source, self.style, self.query, app.nb.get_setting("jamendo_client_id"),
                        self.publish_only, self.page, self.on_results)

    def on_results(self, res, err):
        if err:
            self.status.text = err
            if "client_id" in err or "Jamendo" in err:
                App.get_running_app().settings()
            return
        self.results += res
        self.status.text = f"{len(self.results)} bases" if self.results else "Sin resultados: prueba otro estilo o fuente"
        self.fill()

    def fill(self):
        if not hasattr(self, "box"):
            return
        self.box.clear_widgets()
        for t in self.results:
            self.box.add_widget(self.card(t))
        if self.results:
            more = Factory.FlatButton(text="Más resultados", color=C.rec, size_hint_y=None, height=dp(44))
            more.bind(on_release=lambda *_: (setattr(self, "page", self.page + 1), self.search()))
            self.box.add_widget(more)

    def card(self, t):
        app = App.get_running_app()
        folder = beats.user_dir(app.data_dir)
        have = os.path.exists(os.path.join(folder, discover.safe_name(t) + ".mp3"))
        box = Factory.Surface(orientation="vertical", size_hint_y=None, height=dp(108), padding=dp(12), spacing=dp(2))
        title = Label(text=t["title"], bold=True, font_size="15sp", size_hint_y=None, height=dp(22), halign="left", shorten=True)
        lic = discover.license_label(t["license"])
        pub = "[color=9CCC65]sirve para publicar[/color]" if t["publish_ok"] else "[color=F5A623]solo uso personal[/color]"
        dur = fmt_time(t["duration"]) if t["duration"] else "—"
        info = Label(text=f"{esc(t['artist'])} · {dur} · {lic} · {pub}", markup=True,
                     color=C.muted, font_size="12sp", size_hint_y=None, height=dp(20), halign="left", shorten=True)
        src = Label(text=t["source"], color=C.muted, font_size="11sp", size_hint_y=None, height=dp(16), halign="left")
        for l in (title, info, src):
            l.bind(size=lambda w, sz: setattr(w, "text_size", sz))
            box.add_widget(l)
        row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        play = Factory.FlatButton(text="■ Parar" if self._is_playing(t) else "▶ Escuchar", font_name="DejaVuSans", font_size="14sp")
        play.bind(on_release=lambda *_: self.preview(t))
        dl = Factory.RecButton(text="Descargada" if have else "Descargar", font_size="14sp")
        if not have:
            dl.bind(on_release=lambda *_: self.download(t, dl))
        row.add_widget(play); row.add_widget(dl)
        box.add_widget(row)
        return box

    # escuchar antes de bajar
    _preview = None
    _preview_id = None

    def _is_playing(self, t):
        return self._preview is not None and self._preview_id == t["id"]

    def stop_preview(self):
        if self._preview:
            self._preview.stop()
        self._preview, self._preview_id = None, None

    def preview(self, t):
        was = self._is_playing(t)
        self.stop_preview()
        if not was:
            snd = SoundLoader.load(t["stream"])
            if not snd:
                self.status.text = "No se pudo reproducir (en el PC no hay streaming; en el teléfono sí)"
            else:
                snd.play()
                self._preview, self._preview_id = snd, t["id"]
        self.fill()

    def download(self, t, btn):
        app = App.get_running_app()
        btn.text = "Bajando… 0%"

        def done(path, err):
            if err:
                btn.text = "Reintentar"
                self.status.text = f"No se pudo descargar: {err}"
                return
            btn.text = "Descargada"
            self.status.text = "Lista: ya aparece en Freestyle y al elegir base de una canción"
        discover.download(t, beats.user_dir(app.data_dir), done,
                          progress=lambda p: setattr(btn, "text", f"Bajando… {int(p * 100)}%"))

    def leave(self):
        self.stop_preview()
        App.get_running_app().open_freestyle()


class PrompterScreen(Screen):
    """Teleprompter: suena la base, la letra avanza una barra por compás y se graba la toma."""
    song_id = None

    def on_pre_enter(self):
        self.running = False
        self.render()

    def render(self):
        app = App.get_running_app()
        song = app.nb.song(self.song_id)
        self.clear_widgets()
        if not song:
            return
        self.song = song
        root = BoxLayout(orientation="vertical")
        root.add_widget(top_bar(f"Grabar · {song.title}", self.leave))
        self.rows = []
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10), padding=dp(20))
        box.bind(minimum_height=box.setter("height"))
        current = None
        for b in app.nb.bars(song.id):
            if b.section != current:
                current = b.section
                h = Label(text=(current or "").upper(), color=C.rec, bold=True, size_hint_y=None, height=dp(26), halign="left")
                h.bind(size=lambda w, sz: setattr(w, "text_size", sz))
                box.add_widget(h)
            l = Label(text=b.text, font_name=MONO, font_size="21sp", color=C.muted, size_hint_y=None, halign="left")
            l.bind(width=lambda w, v: setattr(w, "text_size", (v, None)), texture_size=lambda w, sz: setattr(w, "height", sz[1]))
            box.add_widget(l)
            self.rows.append(l)
        box.add_widget(Widget(size_hint_y=None, height=Window.height * .4))
        self.scroll = ScrollView(do_scroll_x=False)
        self.scroll.add_widget(box)
        root.add_widget(self.scroll)
        beat = os.path.splitext(os.path.basename(song.beat))[0] if song.beat else "sin base (solo voz)"
        self.status = Label(text=f"{beat} · {song.bpm} BPM · una barra por compás", color=C.muted, font_size="13sp",
                            size_hint_y=None, height=dp(24))
        root.add_widget(self.status)
        bottom = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(130), padding=dp(8))
        self.dot = RecDot(pos_hint={"center_x": .5})
        self.dot.bind(on_release=lambda *_: self.toggle())
        bottom.add_widget(self.dot)
        root.add_widget(bottom)
        self.add_widget(root)

    def toggle(self):
        if self.running:
            return self.stop()
        speech.ask_mic_permission(lambda ok: self.start(ok))

    def start(self, mic_ok):
        app = App.get_running_app()
        self.running, self.line = True, -1
        self.recording = mic_ok and recorder.available()
        if self.recording:
            self.path = os.path.join(app.takes_dir(), f"toma_{self.song.id}_{int(time.time())}.m4a")
            app.recorder.start(self.path)
        app.beat.play(self.song.beat, self.song.bpm, self.on_beat)
        self.dot.pulse(True)
        self.status.text = "Cuenta: 1"
        self.status.color = C.rec

    def on_beat(self, n):
        if n <= 4:  # un compás de cuenta antes de empezar
            self.status.text = "Cuenta: " + " ".join(str(i) for i in range(1, n + 1)) if n < 4 else "¡Ahora!"
            if n < 4:
                return
        if n % 4 != 0:
            return
        self.line += 1
        for i, l in enumerate(self.rows):
            l.color = C.chalk if i == self.line else C.muted
        if self.line < len(self.rows):
            self.scroll.scroll_to(self.rows[self.line], padding=dp(120), animate={"d": .3})
            self.status.text = f"Barra {self.line + 1} de {len(self.rows)}" + ("  ·  REC" if self.recording else "")
        else:
            self.stop()

    def stop(self, save=True):
        if not self.running:
            return
        app = App.get_running_app()
        self.running = False
        app.beat.stop()
        self.dot.pulse(False)
        self.status.color = C.muted
        if self.recording:
            dur = app.recorder.stop()
            if save:
                n = len(app.nb.takes(self.song.id)) + 1
                app.nb.add_take(self.path, dur, self.song.id, "", f"Toma {n}")
                self.status.text = f"Toma {n} guardada ({fmt_time(dur)})"
                return
        self.status.text = "Listo" if recorder.available() else "Listo (grabar audio solo funciona en el teléfono)"

    def leave(self):
        self.stop()
        App.get_running_app().open_song(self.song.id)

    def on_leave(self):
        self.stop()


def system_bar_insets() -> tuple[float, float]:
    """Alto (px) de la barra de estado y de navegación en Android; (0, 0) en el PC."""
    from kivy.utils import platform
    if platform != "android":
        return 0, 0
    try:
        from jnius import autoclass
        res = autoclass("org.kivy.android.PythonActivity").mActivity.getResources()

        def dim(name):
            i = res.getIdentifier(name, "dimen", "android")
            return res.getDimensionPixelSize(i) if i > 0 else 0
        return dim("status_bar_height"), dim("navigation_bar_height")
    except Exception:
        return dp(28), dp(24)


# ---------- app ----------

class CompasZeroApp(App):
    title = "CompásZero"
    icon = os.path.join(HERE, "assets", "icon.png")

    def build(self):
        Window.clearcolor = C.ink
        Window.softinput_mode = "below_target"
        data_dir = self.data_dir = os.getenv("CZ_DATA") or self.user_data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.nb = Notebook(os.path.join(data_dir, "cuaderno.db"))
        self.rhymes = RhymeIndex()
        self.speller = Speller(personal=self.nb.personal_words())
        self.thesaurus = Thesaurus()
        self.beat = BeatPlayer()
        self.recorder = recorder.Recorder()
        self._take_sound = None
        self.rhyme_kind = None  # tipo de rima activo (None = modo rimas apagado)
        self.sm = ScreenManager(transition=NoTransition())
        # Android 15 dibuja la app detrás de la barra de estado y la de navegación:
        # dejamos ese espacio libre para que no tapen los botones de arriba y abajo.
        top, bottom = system_bar_insets()
        frame = BoxLayout(padding=(0, top, 0, bottom))
        with frame.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*C.ink)
            bg = Rectangle()
        frame.bind(pos=lambda w, p: setattr(bg, "pos", p), size=lambda w, sz: setattr(bg, "size", sz))
        for s in (IntroScreen(name="intro"), HomeScreen(name="home"), SongScreen(name="song"),
                  FreestyleScreen(name="freestyle"), ReviewScreen(name="review"), PrompterScreen(name="prompter"), DiscoverScreen(name="discover")):
            self.sm.add_widget(s)
        Window.bind(on_keyboard=self.on_back)
        frame.add_widget(self.sm)
        return frame

    def on_back(self, window, key, *args):
        if key == 27 and self.sm.current == "discover":
            self.sm.current_screen.leave()
            return True
        if key == 27 and self.sm.current == "prompter":
            self.sm.current_screen.leave()
            return True
        if key == 27 and self.sm.current == "freestyle":
            self.sm.current_screen.leave()
            return True
        if key == 27 and self.sm.current in ("song", "review"):  # botón atrás de Android
            self.go_home()
            return True
        return False

    def refresh(self):
        self.sm.current_screen.render()

    def go_home(self):
        self.sm.current = "home"

    def toast(self, msg):
        if msg:
            dialog(msg, Label(size_hint_y=None, height=dp(4)), [("OK", lambda: None, False)])

    # ---- tomas y notas de voz ----
    def stop_take_playback(self):
        if self._take_sound:
            self._take_sound.stop()
            self._take_sound = None

    def play_take(self, path):
        playing = self._take_sound is not None and getattr(self, "_take_path", None) == path
        self.stop_take_playback()
        if not playing:
            self._take_sound = SoundLoader.load(path)
            self._take_path = path
            if self._take_sound:
                self._take_sound.play()

    def take_row(self, tk, refresh):
        when = time.strftime("%d/%m %H:%M", time.localtime(tk.created_at))
        c = Card(title=f"{tk.name or 'Toma'}  ·  {fmt_time(tk.duration)}", subtitle=f"{tk.section or ''} {when} · tocar: escuchar")
        c.height = dp(64)
        c.bind(on_release=lambda *_: self.play_take(tk.path))
        hold = {}

        def down(w, touch):
            if w.collide_point(*touch.pos):
                hold["ev"] = Clock.schedule_once(lambda dt: dialog("¿Borrar esta grabación?", Label(size_hint_y=None, height=dp(4)), [
                    ("Cancelar", lambda: None, False),
                    ("Borrar", lambda: (self.stop_take_playback(), self.nb.delete_take(tk.id), refresh()), True)]), .7)

        def up(w, touch):
            if hold.get("ev"):
                hold["ev"].cancel()
        c.bind(on_touch_down=down, on_touch_up=up)
        return c

    def takes_dir(self):
        d = os.path.join(self.data_dir, "tomas")
        os.makedirs(d, exist_ok=True)
        return d

    def toggle_voice_note(self, refresh):
        if self.recorder.recording:
            dur = self.recorder.stop()
            n = len(self.nb.voice_notes()) + 1
            self.nb.add_take(self.recorder.path, dur, name=f"Nota de voz {n}")
            return refresh()
        if not recorder.available():
            return self.toast("Grabar solo funciona en el teléfono")

        def go(ok):
            if not ok:
                return self.toast("Sin permiso de micrófono")
            self.recorder.start(os.path.join(self.takes_dir(), f"nota_{int(time.time())}.m4a"))
            refresh()
        speech.ask_mic_permission(go)

    # ---- canción ----
    def song_menu(self, song):
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        body.bind(minimum_height=body.setter("height"))
        body.add_widget(Label(text="Estado", color=C.muted, size_hint_y=None, height=dp(18), halign="left",
                              text_size=(Window.width * .8, None)))
        st = StackLayout(size_hint_y=None, spacing=dp(6))
        st.bind(minimum_height=st.setter("height"))
        for x in STATUSES:
            c = Factory.Chip(text=x, group="status", state="down" if song.status == x else "normal")
            c.bind(on_release=lambda w, x=x: (self.nb.set_song(song.id, status=x), self.refresh()))
            st.add_widget(c)
        body.add_widget(st)
        tags = text_input(song.tags, hint="#etiquetas  #barrio #amor", lyric=False)
        body.add_widget(tags)
        actions = [
            ("Grabar con teleprompter", lambda: self.open_prompter(song.id)),
            ("Elegir base y BPM", lambda: self.pick_song_beat(song)),
            ("Versiones anteriores", lambda: self.show_versions(song)),
            ("Compartir letra", lambda: self.toast(android_io.share_text(song.title, self.nb.song_text(song.id)))),
            ("Borrar canción", lambda: self.confirm_delete(song)),
        ]
        holder = {}
        for text, cb in actions:
            b = Factory.FlatButton(text=text, size_hint_y=None, height=dp(42), halign="left",
                                   color=C.rec if text.startswith("Borrar") else C.chalk)
            b.bind(size=lambda w, sz: setattr(w, "text_size", sz))
            b.bind(on_release=lambda w, cb=cb: (holder["mv"].dismiss(), save_tags(), cb()))
            body.add_widget(b)

        def save_tags():
            if tags.text != song.tags:
                self.nb.set_song(song.id, tags=tags.text.strip())
        holder["mv"] = dialog(song.title, body, [("Listo", lambda: (save_tags(), self.refresh()), False)])

    def pick_song_beat(self, song):
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        body.bind(minimum_height=body.setter("height"))
        state = {"beat": song.beat}
        bpm = text_input(str(song.bpm), hint="BPM", lyric=False)
        bpm.input_filter = "int"
        bpm.input_type = "number"
        row = StackLayout(size_hint_y=None, spacing=dp(6))
        row.bind(minimum_height=row.setter("height"))
        for name, path in beats.list_beats(self.data_dir):
            c = Factory.Chip(text=name, group="songbeat", state="down" if path == song.beat else "normal")
            c.bind(on_release=lambda w, path=path: (state.update(beat=path), setattr(bpm, "text", str(bpm_of(path, int(bpm.text or 90))))))
            row.add_widget(c)
        body.add_widget(row)
        body.add_widget(Label(text="BPM (se lee del nombre de la base si lo tiene)", color=C.muted, font_size="12sp",
                              size_hint_y=None, height=dp(18)))
        body.add_widget(bpm)
        dialog("Base de la canción", body, [
            ("Cancelar", lambda: None, False),
            ("Guardar", lambda: (self.beat.stop(), self.nb.set_song(song.id, beat=state["beat"] or "",
                                                                    bpm=max(40, min(220, int(bpm.text or 90)))), self.refresh()), False)])

    def show_versions(self, song):
        self.nb.snapshot(song.id)
        vs = self.nb.versions(song.id)
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        body.bind(minimum_height=body.setter("height"))
        if len(vs) <= 1:
            body.add_widget(Label(text="Todavía no hay versiones anteriores.\nSe guarda una cada vez que sales de la canción con cambios.",
                                  color=C.muted, size_hint_y=None, height=dp(60), halign="center"))
        for v in vs[1:]:
            import json as _json
            lines = _json.loads(v.content)
            when = time.strftime("%d/%m %H:%M", time.localtime(v.created_at))
            preview = " / ".join(t for _, t in lines[:2])
            c = Card(title=f"{when} · {len(lines)} barras", subtitle=preview[:60])
            c.bind(on_release=lambda w, v=v, when=when: dialog(f"¿Volver a la versión del {when}?",
                   Label(text="La letra actual queda guardada en el historial.", color=C.muted, size_hint_y=None, height=dp(30)),
                   [("Cancelar", lambda: None, False), ("Restaurar", lambda: (self.nb.restore(v.id), self.refresh()), True)]))
            body.add_widget(c)
        dialog("Versiones", body, [("Cerrar", lambda: None, False)])

    def start_challenge(self, theme, word):
        sid = self.nb.create_song(theme)
        self.nb.set_song(sid, tags=f"#reto #{word}")
        self.open_song(sid)

    def open_prompter(self, sid):
        s = self.sm.get_screen("prompter")
        s.song_id = sid
        self.sm.current = "prompter"

    # ---- ajustes ----
    def settings(self):
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        body.bind(minimum_height=body.setter("height"))

        def export():
            name = f"compaszero-{time.strftime('%Y%m%d-%H%M')}.json"
            android_io.save_document(name, self.nb.export_json(), "application/json", self.toast)

        def restore(text):
            if not text:
                return self.toast("No se eligió ninguna copia")
            try:
                self.nb.import_json(text)
            except Exception as e:
                return self.toast(f"No se pudo restaurar: {e}")
            self.speller.personal = self.nb.personal_words()
            self.refresh()
            self.toast("Cuaderno restaurado")

        def ask_restore():
            dialog("¿Restaurar una copia?", Label(text="Reemplaza todo el cuaderno actual.", color=C.muted, size_hint_y=None, height=dp(30)),
                   [("Cancelar", lambda: None, False),
                    ("Elegir archivo", lambda: android_io.open_document("application/json", restore), True)])

        words = sorted(self.nb.personal_words())
        body.add_widget(Label(text="Client ID de Jamendo (para Descubrir bases)", color=C.muted, font_size="13sp",
                              size_hint_y=None, height=dp(20), halign="left", text_size=(Window.width * .8, None)))
        jid = text_input(self.nb.get_setting("jamendo_client_id"), hint="pega aquí tu client_id", lyric=False)
        jid.bind(text=lambda w, v: self.nb.set_setting("jamendo_client_id", v.strip()))
        body.add_widget(jid)
        for text, cb in [("Guardar copia de seguridad (Drive, Descargas…)", export),
                         ("Restaurar copia de seguridad", ask_restore)]:
            b = Factory.FlatButton(text=text, size_hint_y=None, height=dp(44), halign="left")
            b.bind(size=lambda w, sz: setattr(w, "text_size", sz), on_release=lambda w, cb=cb: (holder["mv"].dismiss(), cb()))
            body.add_widget(b)
        body.add_widget(Label(text=f"Mi diccionario: {', '.join(words) if words else '(vacío)'}", color=C.muted,
                              font_size="13sp", size_hint_y=None, height=dp(40), halign="left",
                              text_size=(Window.width * .8, None)))
        body.add_widget(Label(text="Las grabaciones de audio no van en la copia: se guardan en el teléfono.", color=C.muted,
                              font_size="12sp", size_hint_y=None, height=dp(36), halign="left",
                              text_size=(Window.width * .8, None)))
        holder = {}
        holder["mv"] = dialog("Ajustes", body, [("Cerrar", lambda: None, False)])

    def open_freestyle(self):
        self.sm.current = "freestyle"

    def open_review(self, session_id):
        s = self.sm.get_screen("review")
        s.session_id = session_id
        if self.sm.current == "review":
            s.render()
        self.sm.current = "review"

    def open_song(self, sid):
        s = self.sm.get_screen("song")
        s.song_id = sid
        if self.sm.current == "song":
            s.render()
        self.sm.current = "song"

    def new_song(self):
        t = text_input(hint="Título", lyric=False)
        dialog("Nueva canción", t, [("Cancelar", lambda: None, False),
                                    ("Crear", lambda: self.open_song(self.nb.create_song(t.text)), False)])
        Clock.schedule_once(lambda dt: setattr(t, "focus", True), .2)

    def rename(self, song):
        t = text_input(song.title, lyric=False)
        dialog("Título", t, [("Cancelar", lambda: None, False),
                             ("Guardar", lambda: (self.nb.rename_song(song.id, t.text), self.refresh()), False)])

    def confirm_delete(self, song):
        dialog(f"¿Borrar \"{song.title}\"?", Label(text="Se borran también sus barras.", color=C.muted,
                                                  size_hint_y=None, height=dp(30)),
               [("Cancelar", lambda: None, False),
                ("Borrar", lambda: (self.nb.delete_song(song.id), self.go_home()), True)])

    def edit_bar(self, bar):
        t, box = lyric_editor(bar.text)
        dialog("Editar barra", box, [
            ("Borrar", lambda: (self.nb.delete_bar(bar.id), self.refresh()), True),
            ("Guardar", lambda: (self.nb.update_bar(bar.id, t.text), self.refresh()), False)])

    def idea_actions(self, bar):
        t, box = lyric_editor(bar.text)
        songs = self.nb.songs()
        body = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        body.bind(minimum_height=body.setter("height"))
        body.add_widget(box)
        state = {"section": "Verso"}
        holder = {}

        def move(sid):
            self.nb.update_bar(bar.id, t.text)
            self.nb.move_idea(bar.id, sid, state["section"])
            holder["mv"].dismiss()
            self.refresh()

        if songs:
            body.add_widget(Label(text="Mover a canción", color=C.muted, size_hint_y=None, height=dp(24)))
            body.add_widget(chips(state["section"], lambda s: state.update(section=s)))
            for s in songs:
                b = Factory.FlatButton(text=f"→ {s.title}", font_name="DejaVuSans", size_hint_y=None, height=dp(40))
                b.bind(on_release=lambda w, sid=s.id: move(sid))
                body.add_widget(b)
        holder["mv"] = dialog("Idea", body, [
            ("Borrar", lambda: (self.nb.delete_bar(bar.id), self.refresh()), True),
            ("Guardar", lambda: (self.nb.update_bar(bar.id, t.text), self.refresh()), False)])


if __name__ == "__main__":
    CompasZeroApp().run()
