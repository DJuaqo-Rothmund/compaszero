"""Instructivo de rimas y métrica para rap.

Cada lección: título, bajada, párrafos, ejemplos y una herramienta para practicar.
En los ejemplos, lo marcado entre *asteriscos* se resalta en la app.
Las herramientas: "rima" (analiza una palabra) o "metrica" (analiza una barra).
"""

LESSONS = [
    {
        "id": "rima",
        "title": "¿Qué es una rima?",
        "subtitle": "Sonidos que se repiten al final",
        "body": [
            "Dos palabras riman cuando suenan igual desde su sílaba acentuada (la tónica) hasta el final.",
            "Por eso lo primero es encontrar la tónica: en «camino» es «mi», en «corazón» es «zón», en «rápido» es «rá».",
            "Desde esa vocal hacia el final es donde tiene que coincidir el sonido. Lo de antes no importa.",
        ],
        "examples": ["ca*mino* / des*tino*", "cora*zón* / ra*zón*", "*rápido* / *pálido*"],
        "tool": "rima",
    },
    {
        "id": "consonante",
        "title": "Rima consonante",
        "subtitle": "Vocales y consonantes iguales",
        "body": [
            "Coinciden todos los sonidos desde la tónica: vocales y consonantes.",
            "Es la rima más fuerte y clara. Bien usada pega duro; abusada suena predecible (amor / dolor).",
            "En la app se compara como suena en Latinoamérica: b = v, s = z = c (ce, ci), ll = y y la h no suena.",
        ],
        "examples": ["En la *noche* / sin *reproche*", "Vuelo sin *alas* / esquivo las *balas*",
                     "Mi *voz* / es *veloz*"],
        "tool": "rima",
    },
    {
        "id": "asonante",
        "title": "Rima asonante",
        "subtitle": "Solo las vocales",
        "body": [
            "Coinciden solo las vocales desde la tónica; las consonantes pueden cambiar.",
            "Da muchísima libertad y es la base del rap en español: suena natural y no fuerza las palabras.",
            "En diptongos cuenta la vocal fuerte: «cielo» suena e-o, igual que «pecho».",
        ],
        "examples": ["ca*mino* (i-o) / cu*chillo* (i-o)", "la *calle* (a-e) / mi *madre* (a-e)",
                     "*cielo* (e-o) / *pecho* (e-o)"],
        "tool": "rima",
    },
    {
        "id": "multi",
        "title": "Rima multisilábica",
        "subtitle": "Varias sílabas que riman seguidas",
        "body": [
            "Riman dos, tres o más sílabas seguidas, a veces repartidas entre varias palabras.",
            "Es la marca del rap técnico: mientras más sílabas coinciden, más impacto.",
            "Truco: escribe las vocales de tu final (por ejemplo a-i-o) y busca otras palabras o frases con las mismas.",
        ],
        "examples": ["mi *camino* / tu *latino* / un *palito* (a-i-o)", "con la *mente* / con la *gente* (o-a-e-e)",
                     "*sin frenar* / *mi verdad* (i-e-a)"],
        "tool": "rima",
    },
    {
        "id": "interna",
        "title": "Rima interna",
        "subtitle": "Rimas dentro de la misma barra",
        "body": [
            "No todo rima al final: puedes meter rimas en medio de la barra para darle ritmo.",
            "Funciona muy bien con asonantes cortas que caen en los tiempos fuertes del beat.",
        ],
        "examples": ["*Rimo* en el *ritmo*, mi *ritmo* es mi *signo*",
                     "Con *calma* y con *alma*, la *palma* me *salva*"],
        "tool": None,
    },
    {
        "id": "esquemas",
        "title": "Esquemas de rima",
        "subtitle": "AABB, ABAB, ABBA, AAAA",
        "body": [
            "El esquema dice qué barras riman entre sí. Cada letra es un sonido de rima.",
            "AABB (pareadas): riman de a dos seguidas. Es el más común en rap.",
            "ABAB (cruzadas): rima la 1 con la 3 y la 2 con la 4. Da sorpresa.",
            "ABBA (abrazadas): la 1 con la 4 y las del medio entre sí.",
            "AAAA (monorrima): todas igual; ideal para cerrar un verso con fuerza.",
            "En tus canciones, la app pinta del mismo color los finales que riman: así ves tu esquema de un vistazo.",
        ],
        "examples": ["A: Camino solo por la *calle*", "A: buscando lo que nadie *sabe*",
                     "B: con el corazón en la *mano*", "B: y el micro como mi *hermano*"],
        "tool": None,
    },
    {
        "id": "silabas",
        "title": "Sílabas y métrica",
        "subtitle": "Contar para encajar en el compás",
        "body": [
            "La métrica es cuántas sílabas tiene cada barra. Barras parecidas en sílabas suenan parejas sobre el beat.",
            "La app cuenta dos números: las sílabas de las palabras y las sílabas al rapear (con sinalefa).",
            "No tienen que ser idénticas: lo importante es que cada barra quepa cómoda en su compás.",
        ],
        "examples": ["Antes del beat, nace la idea → 11 sílabas, 10 al rapear"],
        "tool": "metrica",
    },
    {
        "id": "sinalefa",
        "title": "Sinalefa",
        "subtitle": "Cuando dos vocales se unen",
        "body": [
            "Si una palabra termina en vocal y la siguiente empieza con vocal, al hablar se pronuncian juntas en una sola sílaba.",
            "La h no suena, así que no la impide: «todo el humo» se dice to-doel-hu-mo.",
            "Úsala a tu favor para comprimir palabras, o rómpela con una pausa si quieres marcar algo.",
        ],
        "examples": ["nace_la_idea → na-ce-laI-de-a (5, no 6)", "todo_el humo → to-doel-hu-mo (4)"],
        "tool": "metrica",
    },
    {
        "id": "acento",
        "title": "Agudas, llanas y esdrújulas",
        "subtitle": "Dónde cae el acento final",
        "body": [
            "Aguda: acento en la última sílaba (corazón, verdad). Llana: en la penúltima (camino, calle). Esdrújula: en la antepenúltima (rápido, música).",
            "En poesía clásica se suma 1 sílaba si la barra termina en aguda y se resta 1 si termina en esdrújula.",
            "En rap lo clave es que la sílaba tónica de la rima caiga en un golpe del beat: ahí la rima se siente.",
        ],
        "examples": ["Aguda: mi cora*zón*", "Llana: mi ca*mi*no", "Esdrújula: el más *rá*pido"],
        "tool": "metrica",
    },
    {
        "id": "compas",
        "title": "Compás, barras y BPM",
        "subtitle": "Escribir pensando en el beat",
        "body": [
            "Casi todo el hip hop va en 4/4: cada compás tiene 4 tiempos. En rap, una barra suele ser un compás.",
            "La caja (snare) golpea en los tiempos 2 y 4: los finales de barra que caen ahí pegan más.",
            "Los BPM dicen la velocidad. A 90 BPM un compás dura unos 2,7 segundos.",
            "Si rapeas en corcheas caben unas 8 sílabas por barra; en semicorcheas, unas 16. El doble tiempo va aún más rápido.",
            "Un verso típico tiene 16 barras; un coro, 8.",
        ],
        "examples": ["90 BPM · corcheas ≈ 8 sílabas por barra", "90 BPM · semicorcheas ≈ 16 sílabas por barra"],
        "tool": "metrica",
    },
    {
        "id": "flow",
        "title": "Flow y punchline",
        "subtitle": "Cómo suena lo que escribes",
        "body": [
            "El flow es cómo repartes las sílabas sobre el beat: dónde aceleras, dónde frenas y dónde haces silencio.",
            "El punchline es el remate: la frase más fuerte, normalmente al final de un bloque de 4 barras.",
            "Prueba la misma barra con flows distintos en el teleprompter y quédate con la toma que mejor suene.",
        ],
        "examples": ["Barras 1-3: preparas la idea", "Barra 4: *punchline* que cierra con la rima más fuerte"],
        "tool": None,
    },
]


def parts(example: str):
    """Divide un ejemplo en trozos [(texto, resaltado)] según los *asteriscos*."""
    out, hi = [], False
    for i, chunk in enumerate(example.split("*")):
        if chunk:
            out.append((chunk, hi))
        hi = not hi
    return out
