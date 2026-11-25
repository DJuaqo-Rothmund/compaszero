"""Grabación de voz (tomas sobre la base y notas de voz) con MediaRecorder de Android."""
import os
import time

from kivy.utils import platform


def available() -> bool:
    return platform == "android"


class Recorder:
    def __init__(self):
        self.rec = None
        self.path = None
        self.t0 = 0.0

    def start(self, path: str):
        from jnius import autoclass
        MediaRecorder = autoclass("android.media.MediaRecorder")
        AudioSource = autoclass("android.media.MediaRecorder$AudioSource")
        OutputFormat = autoclass("android.media.MediaRecorder$OutputFormat")
        AudioEncoder = autoclass("android.media.MediaRecorder$AudioEncoder")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        r = MediaRecorder()
        r.setAudioSource(AudioSource.MIC)
        r.setOutputFormat(OutputFormat.MPEG_4)
        r.setAudioEncoder(AudioEncoder.AAC)
        r.setAudioEncodingBitRate(128000)
        r.setAudioSamplingRate(44100)
        r.setOutputFile(path)
        r.prepare()
        r.start()
        self.rec, self.path, self.t0 = r, path, time.monotonic()

    def stop(self) -> float:
        """Detiene y devuelve la duración en segundos."""
        if not self.rec:
            return 0.0
        try:
            self.rec.stop()
        except Exception:  # grabación demasiado corta
            pass
        self.rec.release()
        self.rec = None
        return time.monotonic() - self.t0

    @property
    def recording(self) -> bool:
        return self.rec is not None
