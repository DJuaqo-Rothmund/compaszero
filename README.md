# CompásZero 🎤📓

Cuaderno de rimas para Android: escribe frases sueltas, recibe sugerencias de rima, revisa ortografía, busca bases gratuitas y graba tus versos sobre el beat.

> **Compás** = la métrica del verso (y del beat). **Zero** = la hoja en blanco, el punto de partida.

## Funciones (MVP → futuro)

### 1. Cuaderno (núcleo)
- **Libretas** → **Canciones** → **Secciones** (intro, verso, coro, puente, outro).
- **Barras sueltas**: botón rápido "+ barra" para anotar una frase en 2 segundos (también desde widget o notificación).
- **Banco de ideas**: frases sin canción asignada; arrastrarlas luego a una canción.
- Etiquetas (temas, estados de ánimo), búsqueda y favoritos.
- Autoguardado, historial de versiones y modo sin conexión.

### 2. Asistente de rimas
- Rimas **consonantes** y **asonantes** en español (por la vocal tónica y lo que sigue).
- **Rimas multisilábicas** e internas, resaltadas con colores en el texto.
- **Contador de sílabas** por barra (para encajar en el compás).
- Sugerencias discretas: se activan al tocar la última palabra o en un panel lateral, nunca invasivas.
- Diccionario de sinónimos y jerga/slang.

### 3. Ortografía
- Revisión en español (diccionario Hunspell es_ES / es_419) con subrayado.
- Opción para **ignorar palabras de jerga** y diccionario personal (el rap rompe reglas a propósito).

### 4. Bases (beats)
- Catálogo de **beats gratuitos con licencia libre** (Free Music Archive, ccMixter, Jamendo, beats propios subidos por el usuario).
- Filtros por **BPM**, estilo (boom bap, trap, drill, lo-fi, jazz rap) y tono.
- Reproductor con loop, velocidad y **metrónomo**.
- Vincular una base a cada canción.
- ⚠️ Mostrar siempre licencia y autor; no usar YouTube "type beats" sin permiso.

### 5. Grabación
- Grabar tomas **sobre la base** (con auriculares) o a capela.
- Tomas asociadas a cada sección, con nombre y marcador de tiempo.
- **Modo teleprompter**: la letra se desplaza mientras grabas.
- Exportar/compartir audio (m4a) y letra (texto/PDF).

### 6. Extras con sentido
- **Modo freestyle**: palabra aleatoria cada X compases sobre la base.
- Reto diario (una palabra/tema al día) y racha de escritura.
- Modo oscuro por defecto, tipografía grande y legible.
- Copia de seguridad en Google Drive.

## Stack
| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3 |
| UI | Kivy 2.3 (`src/main.py` + `src/compaszero.kv`) |
| Empaquetado Android | Buildozer / python-for-android (`buildozer.spec`) |
| Datos locales | SQLite (`src/cz/db.py`) |
| Sílabas / rimas | Motor propio en español (`src/cz/syllables.py`) |
| Audio (próximo) | `kivy.core.audio` + `android.media` vía pyjnius |

## Identidad visual

![Logo](docs/brand/logo.svg)

**Lema:** *Antes del beat, nace la idea.*

El símbolo es un **0** atravesado por una línea vertical (barra de compás / cursor / micrófono) con un **punto rojo** (REC). Resume la app: hoja en blanco + ritmo + grabar.

| Token | Color | Uso |
|---|---|---|
| Negro tinta | `#0E0E0E` | Fondo principal (modo oscuro por defecto) |
| Blanco tiza | `#F5F5F5` | Texto, trazos, iconos |
| Rojo REC | `#E5194B` | Grabar, acentos, rima activa (usar poco) |
| Gris grafito | `#2A2A2A` / `#8A8A8A` | Tarjetas, texto secundario |

- **Tipografías:** grafiti solo para el logo y títulos grandes; *Inter/Roboto* en la UI; mono (*JetBrains Mono*) para las letras, para alinear sílabas.
- **El punto rojo es el botón de grabar** en toda la app; parpadea mientras graba.
- Archivos: `docs/brand/logo.svg` (logo completo) y `docs/brand/icon.svg` (símbolo), basados en el vector original `docs/brand/source-illustrator.svg`; el punto rojo late (100% → 40%) con halo.
- **La línea vertical** marca el pulso: en el editor puede moverse al tempo de la base como metrónomo visual.
- Rimas resaltadas con subrayados tipo spray (blanco, rojo y variaciones de gris/rosa).
- Salpicaduras de spray en estados vacíos ("Tu primera barra empieza aquí").
- **Icono Android:** `src/assets/icon.png`; solo el 0 con punto rojo sobre negro; versión monocroma para Android 13+. El texto grafiti no se lee en tamaño icono.
- **Splash:** el 0 aparece, la línea cae como un beat y el punto rojo se enciende.

## Estado actual (v0.2)
- Intro animada: símbolo con luz REC que late (rojo → casi apagado), grafiti "pintado en vivo" con spray, líneas y lema. Fuente: `docs/brand/intro.svg` (generado con `tools/build_intro.py`); la app reproduce los cuadros de `src/assets/intro.zip`.
- Cuaderno: canciones con secciones (Intro, Verso, Coro, Puente, Outro) y banco de **ideas sueltas** con escritura rápida (Enter guarda y deja listo para la siguiente).
- **Teclado nativo de Android** con autocorrector y sugerencias en todos los campos de letra.
- **Modo rimas**: eliges el tipo (consonante, asonante o multisilábica) y sugiere palabras que riman con la última palabra escrita, o con el final de la barra anterior si el campo está vacío. Tocar una sugerencia la agrega. Motor en `src/cz/rhymes.py`, ~59.000 palabras en `src/assets/rimas_es.tsv`.
- **Freestyle**: eliges una base (dos incluidas, o importas la tuya), tocas el punto rojo y la app transcribe lo que rapeas con el reconocedor de voz de Android, marcando el segundo de cada línea. Después revisas, corriges y mandas las líneas a Ideas o a una canción nueva.
- Contador de sílabas en vivo por barra.

### Probar en el PC
```bash
pip install "kivy[base]==2.3.1" pytest
python src/main.py
python -m pytest tests
CZ_FAKE_SPEECH=1 python src/main.py   # simula el dictado del freestyle en el PC
```

### Generar el APK
```bash
pip install buildozer
buildozer android debug     # APK en bin/
```

## Hoja de ruta
1. **v0.1** – Cuaderno + barras sueltas + contador de sílabas.
2. **v0.2** – Motor de rimas + ortografía.
3. **v0.3** – Reproductor de bases + catálogo libre.
4. **v0.4** – Grabación sobre base + teleprompter.
5. **v1.0** – Backup, freestyle, pulido visual y Play Store.

## Créditos de datos
- Lista de palabras: [wordfreq](https://github.com/rspeer/wordfreq) (CC BY-SA 4.0), regenerable con `tools/build_wordlist.py`.
- Bases incluidas: sintetizadas con `tools/make_beats.py`, originales y libres de derechos.
