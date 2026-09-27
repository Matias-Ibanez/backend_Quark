# Definir los detalles antes de crear una pieza

El agente evalúa el pedido, los adjuntos y los últimos mensajes antes de producir una pieza nueva. Si falta información, pregunta una decisión por vez dentro del chat. Podés tocar una opción o responder desde el cuadro de mensajes. Si el pedido alcanza, la producción empieza directamente. Las elecciones se guardan por conversación y llegan al agente como contexto estructurado.

## Recorrido

1. Escribí el pedido. Se extraen tema, público, objetivo, formato y preferencias que ya diste; no se vuelven a preguntar por rutina.
2. Respondé la pregunta pendiente: tema, formato, duración u otra decisión indispensable. Solo se muestra una a la vez. Las opciones de formato incluyen una referencia visual de proporción; las paletas incluyen muestras.
3. Cuando no queden preguntas, podés abrir **Revisar mis respuestas** y editar una respuesta individual. Pulsá **Crear mi pieza** o escribí `crear` para empezar. Cancelar conserva la conversación y no genera contenido.
4. El resultado aparece como tarjeta compacta en su mensaje. Un clic abre la vista previa; **Archivos** reúne los recursos de ese chat y **Biblioteca** reúne las piezas generadas. Para iterar, escribí el cambio en la misma conversación o usá **Seguir editando** desde la vista previa.

Las decisiones disponibles incluyen público, objetivo, canal, imagen/video/carrusel, proporción, duración de 5–180 segundos, 2–10 láminas, estilo, paleta, tipografía, tono, adjuntos, texto exacto, llamada a la acción, datos confirmados, voz y música. Solo se pregunta lo que falta. Por ejemplo, «creame una imagen» sin contexto pregunta tema y formato; «creá un reel con diseño animado sobre café» pregunta duración y si lleva voz cuando no se indicaron; una imagen cuadrada con tema y dirección visual puede pasar directamente a producción. La evaluación depende del modelo y puede equivocarse; se puede cancelar o corregir por chat.

Cada opción elegida o respuesta enviada se guarda y queda en el historial. El texto todavía sin enviar se conserva durante las actualizaciones periódicas, pero no al recargar. Una versión guardada en otra pestaña reemplaza el borrador anterior; los envíos con versiones desactualizadas se rechazan. Preguntar quién es QUARK durante las aclaraciones no consume la respuesta pendiente.

Un pedido mínimo no significa que el usuario delegó decisiones. Las aclaraciones se presentan de forma neutral; los valores automáticos de estilo, paleta y tipografía son propuestas del agente, no preferencias del usuario. Solo se habla de decisiones delegadas cuando el usuario lo pide expresamente o elige **Elegir por mí**.

La evaluación estructurada usa DeepSeek sin herramientas y registra tokens y costo en `aux_usage`, con origen `creative_intake`. Un pedido mínimo sin tema ni historial abre las preguntas básicas sin llamar al modelo. Ante un fallo o JSON inválido se muestran tema y formato como respaldo; no se produce a partir de una evaluación inválida.

## Validación y entrega

El backend permite guardar respuestas parciales. Antes de confirmar exige tema y público, colores propios cuando se eligen y contenido para el texto exacto. Valida opciones, longitudes, duración, cantidad de láminas, colores HEX y versiones desactualizadas. Una confirmación solo se consume una vez. Si el servicio se reinicia o la producción falla, las respuestas se conservan para reintentar; un pedido automático sin preguntas previas ofrece un campo de detalles para ajustar el intento.

Los detalles de la pieza no reemplazan las instrucciones del agente. Las fechas, precios y contactos ausentes se omiten. Las fuentes o paletas de marca no disponibles admiten una alternativa coherente; para fijarlas, aportá su nombre y colores propios. Las elecciones estéticas orientan al modelo, pero no garantizan por sí solas calidad visual.

Las imágenes y cada lámina del carrusel conservan SVG y PNG. Un carrusel incompleto no se entrega. Las dimensiones de imagen y video, la duración y la voz solicitada se verifican antes de entregar en el chat.

## Elegir cómo se cuenta un video

Short/reel define un formato, no un motor. Si el pedido no define una presentación, QUARK pregunta **¿Cómo te gustaría contar la idea?**, con estas opciones:

- **Escenas reales · clips de referencia:** montaje de biblioteca con MoneyPrinterTurbo. Son escenas ilustrativas; no se presentan como imágenes del local o los clientes reales. La voz se elige por separado; si se eligió sin voz, se elimina la narración del resultado. Se envía la proporción elegida; 4:5 se encuadra localmente desde 9:16 con márgenes para conservar la escena y sus subtítulos.
- **Diseño animado · textos y transiciones:** Hermes carga remotion-best-practices y usa el runtime Remotion instalado para motion graphics, anuncios, tipografía y transiciones.
- **Explicación visual · gráficos y demostraciones:** Hermes carga manimce-best-practices y usa Manim Community para números, diagramas y demostraciones.
- **Con mis fotos · mostrar mi marca:** aparece cuando hay fotos originales adjuntas; Hermes las usa con Remotion, textos y animación de apoyo.

La selección se guarda en `answers.video_mode` y controla la ruta incluso si el pedido dice «short». Se puede responder con botones, `clips`, `diseño animado`, `animaciones` o `mis fotos`; una revisión explícita puede cambiarla. «Un short de 20 segundos sobre mi cafetería» pregunta la dirección; «un short con gráficos de 20 segundos» o «un reel con textos animados de 20 segundos» ya la define. «Animado» por sí solo no decide entre diseño y explicación: se pregunta la dirección. Si el usuario delega expresamente la dirección, se puede proponer una sin repetir la pregunta. Las producciones antiguas sin esta clave conservan su ruta anterior.

Shorts y reels se encuadran en 9:16 salvo que el usuario pida otra proporción. El montaje puede desviarse de la duración al sintetizar la voz: diferencias pequeñas se ajustan sincronizando imagen, subtítulos y narración, sin cambiar el tono de voz. El factor admitido es 0,8–1,25; una diferencia mayor se rechaza en lugar de entregar un resultado incompleto.

Para comunicar por qué una marca es buena o diferente, la evaluación pide sus características confirmadas si no están en el contexto. Los clips no sustituyen esos datos. En el montaje con clips, un PDF aporta únicamente su extracto disponible, marcado como lectura parcial; para una explicación detallada de sus páginas conviene el modo animado, que lee el documento con quark-documents.

## Contrato entre repositorios

`GET /api/projects/{id}/brief` conserva el contrato anterior y agrega `question` (clave pendiente o null) y `answered`. `PUT` guarda, cancela o confirma con `id`, `version`, `answers`, `action` y opcionalmente `field` para guardar una respuesta individual. `POST /api/projects/{id}/brief/reply` acepta `id`, `version` y `message` desde el compositor: interpreta opciones, proporciones y cantidades sin llamar al modelo. Confirmar inicia una sola ejecución y devuelve `run`; las claves permanecen en el servidor. `POST /api/projects/{id}/brief/reopen` permite revisar una pieza terminada. La tabla `brief_responses` conserva el avance, sin modificar mensajes o exportaciones anteriores.

Para volver al flujo anterior se pueden revertir los commits de esta implementación en ambos repositorios. La tabla `project_briefs` puede permanecer sin uso; no se borran conversaciones ni exportaciones anteriores.


## Voz para cualquier video

Al crear un video, QUARK pregunta **¿Querés que el video tenga voz?**, con **Con voz en español** y **Sin voz**, si el pedido no lo especificó. Esto se aplica a explicación visual (Manim), diseño animado (Remotion), originales y escenas reales (MoneyPrinterTurbo). Ni el tipo de video ni una suposición del modelo activan o descartan la voz. La elección se guarda en el chat y se requiere antes de confirmar; también se puede responder «sí», «con voz» o «sin voz».

Si el pedido ya dice con voz, sin voz o con narración, no se repite la pregunta. Las revisiones conservan la elección; «agregá voz» o «quitá la voz» la cambian. Las imágenes y carruseles no muestran esta pregunta. Si se cambia el tipo de pieza a video durante las preguntas, aparece la elección de voz. La locución usa quark-narration y la entrega comprueba la pista de audio antes de adjuntar el video. En Hermes, la guía incluye Edge TTS tanto para Manim como para Remotion.
