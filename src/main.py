"""CompásZero — cuaderno de rimas para rap (Kivy). Antes del beat, nace la idea."""
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import ColorProperty, NumericProperty, StringProperty
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
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.stacklayout import StackLayout
from kivy.factory import Factory

from cz.db import SECTIONS, Bar, Line, Notebook
from cz import beats, speech
from cz.syllables import count_line
from cz.rhymes import TYPES, RhymeIndex, last_word
from cz.theme import C, MONO

HERE = os.path.dirname(os.path.abspath(__file__))
INTRO_SECONDS = 6.0


# ---------- widgets ----------

class Card(ButtonBehavior, BoxLayout):
    title = StringProperty()
    subtitle = StringProperty()


class BarRow(ButtonBehavior, BoxLayout):
    text = StringProperty()
    syllables = NumericProperty(0)

    def __init__(self, bar: Bar, on_pick, **kw):
        super().__init__(text=bar.text, syllables=count_line(bar.text), **kw)
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
        self.count = f"{count_line(text)} sílabas" if text.strip() else ""
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


def brand_title() -> BoxLayout:
    row = BoxLayout(size_hint_x=None, spacing=dp(6))
    a = Label(text="Compás", bold=True, font_size="20sp", size_hint_x=None)
    z = Label(text="Zero", bold=True, font_size="20sp", size_hint_x=None)
    for l in (a, z):
        l.bind(texture_size=lambda w, s: setattr(w, "width", s[0]))
    dot = Label(size_hint=(None, None), size=(dp(8), dp(8)), pos_hint={"center_y": .5})
    with dot.canvas.before:
        from kivy.graphics import Color, Ellipse
        Color(*C.rec)
        e = Ellipse(size=dot.size)
    dot.bind(pos=lambda w, p: setattr(e, "pos", p))
    row.add_widget(a); row.add_widget(dot); row.add_widget(z)
    row.bind(minimum_width=row.setter("width"))
    row.width = dp(140)
    return row


def dialog(title, body, actions) -> ModalView:
    """Diálogo simple: título, contenido y botones [(texto, callback, es_peligroso)]."""
    mv = ModalView(size_hint=(.9, None), background_color=(0, 0, 0, .7), background="")
    box = Factory.Surface(orientation="vertical", padding=dp(16), spacing=dp(12), size_hint_y=None)
    box.bind(minimum_height=box.setter("height"))
    box.add_widget(Label(text=title, bold=True, font_size="18sp", size_hint_y=None, height=dp(30),
                         halign="left", text_size=(Window.width * .8, None)))
    box.add_widget(body)
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


def lyric_editor(value):
    box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(118), spacing=dp(4))
    t = text_input(value, multiline=True)
    n = Label(text=f"{count_line(value)} sílabas", color=C.muted, font_size="12sp",
              size_hint_y=None, height=dp(18), halign="left")
    n.bind(size=lambda w, s: setattr(w, "text_size", s))
    t.bind(text=lambda w, v: setattr(n, "text", f"{count_line(v)} sílabas"))
    box.add_widget(t); box.add_widget(n)
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

    def on_pre_enter(self):
        self.render()

    def render(self):
        app = App.get_running_app()
        self.clear_widgets()
        root = BoxLayout(orientation="vertical")
        top = Factory.TopBar()
        top.add_widget(Label()); top.add_widget(brand_title()); top.add_widget(Label())
        root.add_widget(top)

        layer = FloatLayout()
        if self.tab == 0:
            songs = app.nb.songs()
            body = (empty("Tu primera canción empieza aquí.\nToca + para crearla.") if not songs else
                    scroll_list([self._card(s) for s in songs], spacing=dp(10)))
            layer.add_widget(body)
            fab = Factory.RecButton(text="+", font_size="28sp", size_hint=(None, None), size=(dp(58), dp(58)),
                                    pos_hint={"right": .95, "y": .03})
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
            body = (empty("Anota frases sueltas aquí.\nLuego muévelas a una canción.") if not ideas else
                    scroll_list([BarRow(b, app.idea_actions) for b in ideas]))
            layer.add_widget(body)
            root.add_widget(layer)
            root.add_widget(Composer("Escribe una barra…", lambda t: (app.nb.add_bar(t), self.render()),
                                     context=lambda: ideas[0].text if ideas else ""))

        nav = BoxLayout(size_hint_y=None, height=dp(60))
        for i, name in enumerate(["Canciones", "Ideas", "Freestyle"]):
            b = Factory.FlatButton(text=name, bold=self.tab == i, color=C.rec if self.tab == i else C.muted)
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
        c = Card(title=s.title, subtitle=f"{s.bars} barras")
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


class SongScreen(Screen):
    song_id = None
    section = "Verso"

    def on_pre_enter(self):
        self.render()

    def render(self):
        app = App.get_running_app()
        song = app.nb.song(self.song_id)
        self.clear_widgets()
        if song is None:
            return
        root = BoxLayout(orientation="vertical")
        top = Factory.TopBar()
        back = Factory.FlatButton(text="←", font_name="DejaVuSans", font_size="24sp", size_hint_x=None, width=dp(48))
        back.bind(on_release=lambda *_: app.go_home())
        title = Factory.FlatButton(text=song.title, bold=True, font_size="18sp", halign="left")
        title.bind(size=lambda w, s: setattr(w, "text_size", s), on_release=lambda *_: app.rename(song))
        title.valign = "middle"
        delete = Factory.FlatButton(text="Borrar", color=C.rec, size_hint_x=None, width=dp(72))
        delete.bind(on_release=lambda *_: app.confirm_delete(song))
        for w in (back, title, delete):
            top.add_widget(w)
        root.add_widget(top)

        bars = app.nb.bars(song.id)
        groups: dict[str, list[Bar]] = {}
        for b in bars:
            groups.setdefault(b.section or "Sin sección", []).append(b)
        items = []
        for name in SECTIONS + [k for k in groups if k not in SECTIONS]:
            if name in groups:
                h = Label(text=name.upper(), color=C.rec, bold=True, size_hint_y=None, height=dp(34),
                          halign="left", valign="bottom")
                h.bind(size=lambda w, s: setattr(w, "text_size", s))
                items.append(h)
                items += [BarRow(b, app.edit_bar) for b in groups[name]]
        root.add_widget(scroll_list(items, spacing=dp(6)) if items else empty("Escribe la primera barra abajo."))
        root.add_widget(chips(self.section, self.pick))
        root.add_widget(Composer(f"Barra en {self.section}…",
                                 lambda t: (app.nb.add_bar(t, song.id, self.section), self.render()),
                                 context=lambda: bars[-1].text if bars else ""))
        self.add_widget(root)

    def pick(self, s):
        self.section = s
        self.render()


def fmt_time(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 60}:{sec % 60:02d}"


def top_bar(title, on_back, right=None):
    top = Factory.TopBar()
    back = Factory.FlatButton(text="←", font_name="DejaVuSans", font_size="24sp", size_hint_x=None, width=dp(48))
    back.bind(on_release=lambda *_: on_back())
    t = Label(text=title, bold=True, font_size="18sp", halign="left", valign="middle")
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
        imp = Factory.FlatButton(text="Importar", color=C.rec, size_hint_x=None, width=dp(90))
        imp.bind(on_release=lambda *_: self.import_beat())
        root.add_widget(top_bar("Freestyle", self.leave, imp))

        row = StackLayout(size_hint_y=None, spacing=dp(6), padding=(dp(12), dp(4)))
        row.bind(minimum_height=row.setter("height"))
        for name, path in self.beats:
            c = Factory.Chip(text=name, group="beat", state="down" if path == self.beat else "normal")
            c.bind(on_release=lambda w, p=path: setattr(self, "beat", p))
            row.add_widget(c)
        root.add_widget(row)

        self.lines_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6), padding=dp(16))
        self.lines_box.bind(minimum_height=self.lines_box.setter("height"))
        self.partial = Label(text="", color=C.muted, italic=True, font_name=MONO, size_hint_y=None, halign="left")
        self.partial.bind(width=lambda w, v: setattr(w, "text_size", (v, None)),
                          texture_size=lambda w, s: setattr(w, "height", s[1]))
        self.lines_box.add_widget(self.partial)
        self.scroll = ScrollView(do_scroll_x=False)
        self.scroll.add_widget(self.lines_box)
        root.add_widget(self.scroll)

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
        self.rhyme_kind = None  # tipo de rima activo (None = modo rimas apagado)
        self.sm = ScreenManager(transition=FadeTransition(duration=.35))
        for s in (IntroScreen(name="intro"), HomeScreen(name="home"), SongScreen(name="song"),
                  FreestyleScreen(name="freestyle"), ReviewScreen(name="review")):
            self.sm.add_widget(s)
        Window.bind(on_keyboard=self.on_back)
        return self.sm

    def on_back(self, window, key, *args):
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
