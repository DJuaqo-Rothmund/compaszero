"""CompásZero — cuaderno de rimas para rap (Kivy). Antes del beat, nace la idea."""
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty
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

from cz.db import SECTIONS, Bar, Notebook
from cz.syllables import count_line
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
    """Escritura rápida: Enter guarda y deja el campo listo para la siguiente barra."""
    hint = StringProperty()
    count = StringProperty()

    def __init__(self, hint, on_save, **kw):
        super().__init__(hint=hint, **kw)
        self.on_save = on_save

    def update_count(self, text):
        self.count = f"{count_line(text)} sílabas" if text.strip() else ""

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
        b = Factory.FlatButton(text=text, size_hint_x=None, width=dp(100),
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
        else:
            ideas = app.nb.ideas()
            body = (empty("Anota frases sueltas aquí.\nLuego muévelas a una canción.") if not ideas else
                    scroll_list([BarRow(b, app.idea_actions) for b in ideas]))
            layer.add_widget(body)
            root.add_widget(layer)
            root.add_widget(Composer("Escribe una barra…", lambda t: (app.nb.add_bar(t), self.render())))

        nav = BoxLayout(size_hint_y=None, height=dp(60))
        for i, name in enumerate(["Canciones", "Ideas sueltas"]):
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
                                 lambda t: (app.nb.add_bar(t, song.id, self.section), self.render())))
        self.add_widget(root)

    def pick(self, s):
        self.section = s
        self.render()


# ---------- app ----------

class CompasZeroApp(App):
    title = "CompásZero"
    icon = os.path.join(HERE, "assets", "icon.png")

    def build(self):
        Window.clearcolor = C.ink
        Window.softinput_mode = "below_target"
        data_dir = os.getenv("CZ_DATA") or self.user_data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.nb = Notebook(os.path.join(data_dir, "cuaderno.db"))
        self.sm = ScreenManager(transition=FadeTransition(duration=.35))
        for s in (IntroScreen(name="intro"), HomeScreen(name="home"), SongScreen(name="song")):
            self.sm.add_widget(s)
        Window.bind(on_keyboard=self.on_back)
        return self.sm

    def on_back(self, window, key, *args):
        if key == 27 and self.sm.current == "song":  # botón atrás de Android
            self.go_home()
            return True
        return False

    def refresh(self):
        self.sm.current_screen.render()

    def go_home(self):
        self.sm.current = "home"

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
