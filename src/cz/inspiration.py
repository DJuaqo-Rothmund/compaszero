"""Reto diario, banco de temas y palabras para el freestyle."""
import datetime
import random

TEMAS = [
    "Una calle que te vio crecer", "Lo que nunca le dijiste a tu viejo", "El primer beat que te voló la cabeza",
    "La ciudad de noche desde la micro", "Un amigo que se fue", "Lo que harías con un millón",
    "Tu barrio contado como película", "Carta a tu yo de 15 años", "El silencio antes de subir al escenario",
    "La plata y lo que cambia", "Un amor que fue tormenta", "Las cicatrices que no se ven",
    "El día que casi lo dejas todo", "Lo que aprendiste perdiendo", "Rap como terapia",
    "Una mesa familiar", "El tiempo que no vuelve", "Sueños con olor a cemento",
    "Contra el reloj", "Lo que el espejo no muestra", "La fe cuando no hay nada",
    "Un día normal de laburo", "El ruido de las redes", "La primera vez que te creíste el cuento",
    "Promesas a tu madre", "El hambre (de verdad y de ganas)", "Ser distinto en un lugar igual",
    "Batalla contra ti mismo", "Las luces de la ciudad", "Lo que dejarías escrito",
]

PALABRAS = [
    "fuego", "espejo", "cemento", "reloj", "sombra", "corona", "barrio", "tormenta", "cicatriz", "orgullo",
    "silencio", "calle", "luna", "dinero", "veneno", "raíz", "cadena", "vuelo", "ceniza", "tinta",
    "micrófono", "trueno", "herida", "victoria", "camino", "familia", "frío", "lealtad", "humo", "ritmo",
    "escalera", "cristal", "pantalla", "memoria", "promesa", "puño", "abismo", "semilla", "faro", "laberinto",
    "madrugada", "tren", "ventana", "batalla", "oro", "papel", "cielo", "lluvia", "huella", "bandera",
]


def daily(day: datetime.date | None = None) -> tuple[str, str]:
    """(tema, palabra obligatoria) del día: igual para todo el día, cambia cada día."""
    day = day or datetime.date.today()
    rng = random.Random(day.toordinal())
    return rng.choice(TEMAS), rng.choice(PALABRAS)


def random_theme() -> str:
    return random.choice(TEMAS)


def random_word(exclude: str = "") -> str:
    return random.choice([w for w in PALABRAS if w != exclude])
