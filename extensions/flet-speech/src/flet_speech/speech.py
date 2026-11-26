"""Reconocimiento de voz del sistema (Android/iOS) usando el plugin speech_to_text de Flutter."""
from dataclasses import dataclass
from typing import Optional

import flet as ft


@dataclass
class SpeechResultEvent(ft.Event["SpeechToText"]):
    text: str
    """Lo reconocido hasta ahora en la frase actual."""
    final: bool
    """True cuando la frase terminó (el reconocedor detectó una pausa)."""


@dataclass
class SpeechStatusEvent(ft.Event["SpeechToText"]):
    status: str
    """listening, notListening o done."""


@dataclass
class SpeechErrorEvent(ft.Event["SpeechToText"]):
    message: str
    permanent: bool


@ft.control("SpeechToText")
class SpeechToText(ft.Service):
    """Dictado continuo: escucha, entrega texto parcial/final y avisa cuando se detiene."""

    on_result: Optional[ft.EventHandler[SpeechResultEvent]] = None
    on_status: Optional[ft.EventHandler[SpeechStatusEvent]] = None
    on_error: Optional[ft.EventHandler[SpeechErrorEvent]] = None

    async def initialize(self) -> bool:
        """Pide permiso de micrófono y prepara el reconocedor. Devuelve si está disponible."""
        return bool(await self._invoke_method("initialize", timeout=30))

    async def listen(self, locale: str = "es_ES", pause_for: int = 4, listen_for: int = 120):
        await self._invoke_method("listen", {"locale": locale, "pause_for": pause_for, "listen_for": listen_for})

    async def stop(self):
        await self._invoke_method("stop")

    async def cancel(self):
        await self._invoke_method("cancel")

    async def locales(self) -> list:
        return await self._invoke_method("locales") or []
