"""Dictado continuo con el reconocedor de voz nativo de Android (SpeechRecognizer).

El reconocedor de Android se detiene tras cada pausa, así que se reinicia solo mientras
el freestyle siga activo. Las frases terminadas llegan a `on_final(texto)` y las parciales
(lo que va entendiendo mientras hablas) a `on_partial(texto)`.

En el PC no hay reconocedor: `available()` devuelve False. Para probar la interfaz sin
teléfono se puede definir CZ_FAKE_SPEECH=1 y se simula un freestyle.
"""
import os

from kivy.clock import Clock
from kivy.utils import platform


class _Base:
    def __init__(self, on_partial, on_final, on_error=None, language="es-419"):
        self.on_partial, self.on_final = on_partial, on_final
        self.on_error = on_error or (lambda msg: None)
        self.language = language
        self.active = False


class FakeListener(_Base):
    LINES = ["Antes del beat nace la idea", "rimo con el alma sin pedir permiso",
             "cada barra es un latido", "la calle me enseñó a escribir de noche"]

    def start(self):
        self.active, self._i, self._w = True, 0, 0
        self._ev = Clock.schedule_interval(self._tick, 0.35)

    def _tick(self, dt):
        words = self.LINES[self._i % len(self.LINES)].split()
        self._w += 1
        if self._w < len(words):
            self.on_partial(" ".join(words[: self._w]))
        else:
            self.on_final(" ".join(words))
            self._i, self._w = self._i + 1, 0

    def stop(self):
        self.active = False
        self._ev.cancel()


if platform == "android":
    from android.runnable import run_on_ui_thread
    from jnius import PythonJavaClass, autoclass, java_method

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
    RecognizerIntent = autoclass("android.speech.RecognizerIntent")
    Intent = autoclass("android.content.Intent")

    # códigos de error que solo significan "no escuché nada todavía": se reinicia
    _RETRY = {1, 2, 6, 7, 8}  # timeout de red, red, sin voz, sin coincidencias, ocupado
    _ERRORS = {3: "Error de audio", 4: "Error del servidor de voz", 5: "Error del cliente",
               9: "Falta el permiso de micrófono", 12: "Idioma no soportado", 13: "Idioma no disponible"}

    class _Listener(PythonJavaClass):
        __javainterfaces__ = ["android/speech/RecognitionListener"]
        __javacontext__ = "app"

        def __init__(self, owner):
            super().__init__()
            self.owner = owner

        @staticmethod
        def _texts(bundle):
            arr = bundle.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION) if bundle else None
            return arr.get(0) if arr and arr.size() else ""

        @java_method("(Landroid/os/Bundle;)V")
        def onReadyForSpeech(self, params): pass

        @java_method("()V")
        def onBeginningOfSpeech(self): pass

        @java_method("(F)V")
        def onRmsChanged(self, rms): pass

        @java_method("([B)V")
        def onBufferReceived(self, buf): pass

        @java_method("()V")
        def onEndOfSpeech(self): pass

        @java_method("(I)V")
        def onError(self, code):
            self.owner._error(code)

        @java_method("(Landroid/os/Bundle;)V")
        def onResults(self, results):
            text = self._texts(results)
            Clock.schedule_once(lambda dt: self.owner._final(text))

        @java_method("(Landroid/os/Bundle;)V")
        def onPartialResults(self, partial):
            text = self._texts(partial)
            if text:
                Clock.schedule_once(lambda dt: self.owner.on_partial(text))

        @java_method("(ILandroid/os/Bundle;)V")
        def onEvent(self, event_type, params): pass

    class AndroidListener(_Base):
        def start(self):
            self.active = True
            self._create()

        @run_on_ui_thread
        def _create(self):
            act = PythonActivity.mActivity
            self.rec = SpeechRecognizer.createSpeechRecognizer(act)
            self.listener = _Listener(self)
            self.rec.setRecognitionListener(self.listener)
            self.intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            self.intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            self.intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, self.language)
            self.intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)
            self.intent.putExtra("android.speech.extra.SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS", 1500)
            self.intent.putExtra("android.speech.extra.SPEECH_INPUT_MINIMUM_LENGTH_MILLIS", 10000)
            self.rec.startListening(self.intent)

        @run_on_ui_thread
        def _restart(self):
            if self.active:
                self.rec.cancel()
                self.rec.startListening(self.intent)

        def _final(self, text):
            if text:
                self.on_final(text)
            self._restart()

        def _error(self, code):
            if not self.active:
                return
            if code in _RETRY:
                self._restart()
            else:
                Clock.schedule_once(lambda dt: self.on_error(_ERRORS.get(code, f"Error de voz ({code})")))

        def stop(self):
            self.active = False
            self._destroy()

        @run_on_ui_thread
        def _destroy(self):
            if getattr(self, "rec", None):
                self.rec.stopListening()
                self.rec.destroy()
                self.rec = None


def available() -> bool:
    if os.getenv("CZ_FAKE_SPEECH"):
        return True
    if platform == "android":
        return bool(SpeechRecognizer.isRecognitionAvailable(PythonActivity.mActivity))
    return False


def listener(on_partial, on_final, on_error=None):
    if os.getenv("CZ_FAKE_SPEECH") or platform != "android":
        return FakeListener(on_partial, on_final, on_error)
    return AndroidListener(on_partial, on_final, on_error)


def ask_mic_permission(callback):
    """Pide el permiso de micrófono (Android) y llama a callback(True/False)."""
    if platform != "android":
        return callback(True)
    from android.permissions import Permission, check_permission, request_permissions
    if check_permission(Permission.RECORD_AUDIO):
        return callback(True)
    request_permissions([Permission.RECORD_AUDIO],
                        lambda perms, grants: Clock.schedule_once(lambda dt: callback(all(grants))))
