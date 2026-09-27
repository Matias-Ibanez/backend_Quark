"""Public product knowledge shared by the welcome replies and the agent prompt."""
import re

IDENTITY = (
    "Soy QUARK, tu agente de marketing. Te acompaño desde la idea hasta el contenido: "
    "podemos definir qué comunicar, crear una pieza y mejorarla juntos.\n\n"
    "Podés empezar contándome qué vendés o qué tema querés compartir, aunque todavía no tengas una idea cerrada."
)
CAPABILITIES = (
    "Soy QUARK, tu agente de marketing. Puedo acompañarte con:\n\n"
    "- **Contenido visual:** publicaciones, banners, carruseles, reels y videos cortos.\n"
    "- **Tus fotos:** recortar o separar el producto del fondo e incorporarlo a una pieza.\n"
    "- **Tus documentos:** transformar el contenido de un PDF en una publicación o un video para redes.\n"
    "- **Textos:** títulos, descripciones, llamados a la acción y respuestas para tus clientes.\n"
    "- **Planificación:** ideas de campañas, propuestas para tu público y calendarios de contenido.\n"
    "- **Mejoras:** ajustar el diseño, el mensaje o el ritmo de una pieza que ya hicimos.\n\n"
    "Por ejemplo: «Quiero promocionar mi cafetería en Instagram» o «Tengo esta foto de una remera, armemos una publicación». "
    "¿Querés empezar por una idea, una pieza o un plan para tu marca?"
)
START = (
    "Podemos empezar por lo que ya tengas: una idea, una foto o un objetivo para tu marca. "
    "Si todavía no sabés qué publicar, te ayudo a elegir una dirección.\n\n"
    "Contame qué ofrecés y qué te gustaría lograr: darlo a conocer, conseguir consultas o presentar una promoción. "
    "Con eso te propongo el siguiente paso. Si falta una decisión importante, te mostraré solo las preguntas necesarias."
)
WORKFLOW = (
    "Primero entiendo qué querés comunicar y para quién. Aprovecho lo que ya me contaste y "
    "te pregunto solo las decisiones que falten. Después preparo el contenido y lo revisamos juntos.\n\n"
    "Podés pedirme cambios sobre la misma pieza, como otro título, una paleta distinta o un video más corto. "
    "Los detalles de estilo también podés dejarlos a mi criterio."
)
VISUAL = (
    "Puedo ayudarte con publicaciones, banners y carruseles, además de reels y videos cortos para comunicar tu marca. "
    "Podemos usar formatos cuadrados, verticales u horizontales y estilos editoriales, de producto o tipográficos.\n\n"
    "Trabajo con texto, elementos gráficos y las fotos que aportes; no creo fotografías nuevas. "
    "¿Querés mostrar un producto, anunciar algo o explicar un tema a tu público?"
)
PHOTOS = (
    "Sí. Podés adjuntar una foto de tu producto: puedo recortarla, separar el sujeto del fondo "
    "y combinarla con textos y elementos gráficos para una publicación. Conservamos la foto original para seguir ajustando.\n\n"
    "Por ejemplo, una remera puede ser la protagonista de una pieza con el nombre de tu marca y un llamado a consultar. "
    "¿Qué producto querés mostrar?"
)
DOCUMENTS = (
    "Podés adjuntar un PDF o arrastrarlo al chat. Puedo usar su contenido para preparar "
    "una publicación, un carrusel o un video para redes, eligiendo las ideas que mejor comuniquen tu mensaje.\n\n"
    "Si alguna parte no se puede leer, te lo indicaré antes de usarla. Podés decirme qué páginas o temas querés destacar."
)
TEXTS = (
    "Puedo redactar y mejorar títulos, descripciones de publicaciones, mensajes de promociones, "
    "llamados a la acción y respuestas para clientes de tu marca. Adaptamos el tono a tu público.\n\n"
    "Usaré los datos que me des; no inventaré precios, descuentos ni condiciones. ¿Qué querés comunicar?"
)
PLANNING = (
    "Puedo ayudarte a definir objetivos, público, ideas de campañas y un calendario de contenido para tu marca. "
    "También podemos elegir qué publicar primero y adaptar el mensaje a cada canal.\n\n"
    "No puedo garantizar ventas o resultados. Para empezar, ¿qué ofrecés y qué querés mejorar: visibilidad, consultas o ventas?"
)
INSTAGRAM = (
    "Puedo preparar contenido para Instagram, textos para publicaciones, ideas de calendario "
    "y respuestas sugeridas para tus clientes.\n\n"
    "Desde este chat no publico ni respondo mensajes en tu cuenta automáticamente. "
    "Podemos dejar el contenido o la respuesta listos para que los revises. ¿Cuál de esas tareas necesitás?"
)
MUSIC = (
    "Podemos sumar música de fondo a un video. Podés pedirlo en el chat, buscar una canción o adjuntar un audio; "
    "después elegís y escuchás el tramo que querés usar y dónde empieza en el video. "
    "La música acompaña el contenido de tu marca. ¿Querés agregarla a un video que ya hicimos?"
)
REVISIONS = (
    "En este chat puedo retomar los pedidos y las piezas que trabajamos, para que no tengas que explicar todo de nuevo. "
    "Podés pedir cambios de texto, formato, colores o duración sobre la misma pieza.\n\n"
    "Para continuar un trabajo, volvé a esta conversación. ¿Qué te gustaría ajustar?"
)
LIMITS = (
    "Mi foco es marketing y comunicación de marca: ideas, contenido, campañas y atención a clientes. "
    "No hago programación, tareas personales ajenas a marketing ni asesoramiento profesional fuera de ese ámbito.\n\n"
    "Puedo preparar un contenido educativo para las redes de un creador, pero no resolver una tarea escolar personal. "
    "Tampoco invento datos comerciales, creo fotografías nuevas ni publico o envío mensajes automáticamente desde este chat."
)

# Narrow patterns select known product information; production requests keep their normal route.
REPLIES = [
    (r"\b(?:(?:que|como|para que).{0,65}(?:documentos?|pdf)|(?:puedes|podes) (?:leer|usar|transformar).{0,30}(?:documentos?|pdf))\b", DOCUMENTS),
    (r"\b(?:que (?:cosas )?(?:puedes|podes|podrias|sabes) hacer|que (?:eres|sos) capaz de hacer|(?:cuales|que) son tus (?:capacidades|funciones)|que (?:ofreces|haces)|para que (?:sirves|servis)|(?:en que|como) (?:me )?(?:puedes|podes) ayudar(?:me)?)\b", CAPABILITIES),
    (r"\b(?:que (?:no puedes|no podes) hacer|(?:cuales|que) son tus (?:limites|limitaciones))\b", LIMITS),
    (r"\b(?:quien (?:eres|sos)|que (?:eres|sos)|como te llamas|presentate|quien te creo)\b", IDENTITY),
    (r"\b(?:como (?:funcionas|trabajamos|trabajas)|como es (?:el|tu) proceso|sobre que corres|que (?:modelo|herramientas) usas)\b", WORKFLOW),
    (r"\b(?:como (?:empiezo|empezamos|comienzo)|por donde (?:empiezo|empezamos)|no se (?:que publicar|como empezar)|necesito ideas para mi marca)\b|^ayuda[.!? ]*$", START),
    (r"\b(?:(?:puedes|podes) (?:publicar|responder|gestionar).{0,60}instagram|(?:que|como) .{0,45}(?:haces|ayudas|funciona).{0,30}instagram)\b", INSTAGRAM),
    (r"\b(?:(?:puedes|podes) (?:usar|editar|recortar|trabajar con).{0,35}(?:fotos|foto|imagenes)|(?:como|para que) (?:subo|adjunto).{0,20}(?:foto|imagen))\b", PHOTOS),
    (r"\b(?:(?:puedes|podes) (?:hacer|crear|generar).{0,35}(?:videos|video|reels|reel|imagenes|imagen|carruseles|carrusel)|que (?:formatos|tipos de contenido|estilos) (?:haces|ofreces|puedes crear|podes crear))\b", VISUAL),
    (r"\b(?:(?:puedes|podes) (?:escribir|redactar|mejorar).{0,35}(?:textos|copy|descripciones|respuestas)|que textos (?:haces|ofreces))\b", TEXTS),
    (r"\b(?:(?:puedes|podes) (?:planificar|organizar|armar).{0,35}(?:campanas|calendario|estrategia)|(?:como|en que) .{0,30}ayudas.{0,30}(?:marketing|campanas|ventas))\b", PLANNING),
    (r"\b(?:(?:puedes|podes) (?:agregar|poner|usar).{0,30}(?:musica|canciones)|como (?:agrego|agregar|pongo|poner).{0,20}(?:musica|cancion))\b", MUSIC),
    (r"\b(?:recordas|recuerdas|(?:como|que) .{0,20}(?:memoria|contexto)|(?:puedes|podes) (?:retomar|recordar)|como (?:cambio|modifico|ajusto) (?:una|la|esta) (?:pieza|imagen|publicacion|video))\b", REVISIONS),
]
PRODUCTION_COMMAND = re.compile(
    r"\b(?:creame|haceme|hazme|generame|armame|disename)\b|"
    r"\b(?:quiero|necesito)\s+(?:un|una|otro|otra)\s+(?:post|publicacion|imagen|video|reel|banner|carrusel|logo|texto|copy)\b|"
    r"\b(?:hacer|crear|generar|redactar|recortar|editar|mejorar|armar)\b.{0,100}"
    r"(?:\bsobre\b|\bacerca de\b|\bde \d|\b(?:esta|esa|la) foto\b|\bmi (?:cafeteria|tienda|producto|negocio)\b)|"
    r"\b(?:crea|hace|haz|genera|arma|disena|redacta)\s+(?:(?:un|una|el|la|otro|otra|nuevo|nueva)\s+)?"
    r"(?:post|publicacion|imagen|video|reel|banner|carrusel|logo|texto|copy)\b"
)


def reply(normalized):
    if PRODUCTION_COMMAND.search(normalized):
        return None
    for pattern, response in REPLIES:
        if re.search(pattern, normalized):
            return response
    return None


PUBLIC_PROFILE = "\n\n".join((IDENTITY, CAPABILITIES, WORKFLOW, VISUAL, PHOTOS, TEXTS, PLANNING, INSTAGRAM, MUSIC, REVISIONS, LIMITS))
