# Definir los detalles antes de crear una pieza

El agente evalúa el pedido, los adjuntos y los últimos mensajes antes de producir una pieza nueva. Si falta información, pregunta una decisión por vez dentro del chat. Podés tocar una opción o responder desde el cuadro de mensajes. Si el pedido alcanza, la producción empieza directamente. Las elecciones se guardan por conversación y llegan al agente como contexto estructurado.

## Recorrido

1. Escribí el pedido. Se extraen tema, público, objetivo, formato y preferencias que ya diste; no se vuelven a preguntar por rutina.
2. Respondé la pregunta pendiente: tema, formato, duración u otra decisión indispensable. Solo se muestra una a la vez. Las opciones de formato incluyen una referencia visual de proporción; las paletas incluyen muestras.
3. Cuando no queden preguntas, podés abrir **Revisar mis respuestas** y editar una respuesta individual. Pulsá **Crear mi pieza** o escribí `crear` para empezar. Cancelar conserva la conversación y no genera contenido.
4. El resultado aparece como tarjeta compacta en su mensaje. Un clic abre la vista previa; **Archivos** reúne los recursos de ese chat y **Biblioteca** reúne las piezas generadas. Para iterar, escribí el cambio en la misma conversación o usá **Seguir editando** desde la vista previa.

Las decisiones disponibles incluyen público, objetivo, canal, imagen/video/carrusel, proporción, duración de 5–180 segundos, 2–10 láminas, estilo, paleta, tipografía, tono, adjuntos, texto exacto, llamada a la acción, datos confirmados, voz y música. Solo se pregunta lo que falta. Por ejemplo, «creame una imagen» sin contexto pregunta tema y formato; «creá un reel sobre café» puede preguntar solo duración; una imagen cuadrada con tema y dirección visual puede pasar directamente a producción. La evaluación depende del modelo y puede equivocarse; se puede cancelar o corregir por chat.

Cada opción elegida o respuesta enviada se guarda y queda en el historial. El texto todavía sin enviar se conserva durante las actualizaciones periódicas, pero no al recargar. Una versión guardada en otra pestaña reemplaza el borrador anterior; los envíos con versiones desactualizadas se rechazan. Preguntar quién es QUARK durante las aclaraciones no consume la respuesta pendiente.

Un pedido mínimo no significa que el usuario delegó decisiones. Las aclaraciones se presentan de forma neutral; los valores automáticos de estilo, paleta y tipografía son propuestas del agente, no preferencias del usuario. Solo se habla de decisiones delegadas cuando el usuario lo pide expresamente o elige **Elegir por mí**.

La evaluación estructurada usa DeepSeek sin herramientas y registra tokens y costo en `aux_usage`, con origen `creative_intake`. Un pedido mínimo sin tema ni historial abre las preguntas básicas sin llamar al modelo. Ante un fallo o JSON inválido se muestran tema y formato como respaldo; no se produce a partir de una evaluación inválida.

## Validación y entrega

El backend permite guardar respuestas parciales. Antes de confirmar exige tema y público, colores propios cuando se eligen y contenido para el texto exacto. Valida opciones, longitudes, duración, cantidad de láminas, colores HEX y versiones desactualizadas. Una confirmación solo se consume una vez. Si el servicio se reinicia o la producción falla, las respuestas se conservan para reintentar; un pedido automático sin preguntas previas ofrece un campo de detalles para ajustar el intento.

Los detalles de la pieza no reemplazan las instrucciones del agente. Las fechas, precios y contactos ausentes se omiten. Las fuentes o paletas de marca no disponibles admiten una alternativa coherente; para fijarlas, aportá su nombre y colores propios. Las elecciones estéticas orientan al modelo, pero no garantizan por sí solas calidad visual.

Las imágenes y cada lámina del carrusel conservan SVG y PNG. Un carrusel incompleto no se entrega. Las dimensiones de imagen y video, la duración y la voz solicitada se verifican antes de entregar en el chat.

## Elegir cómo se cuenta un video

Short/reel define un formato, no un motor. Si el pedido no define una presentación, QUARK pregunta **¿Cómo te gustaría contar la idea?**, con estas opciones:

- **Clips reales de referencia · voz y subtítulos:** montaje de biblioteca con MoneyPrinterTurbo. Son escenas ilustrativas; no se presentan como imágenes del local o los clientes reales. Si se pidió sin voz, la opción lo indica y se elimina la narración del resultado. Se envía la proporción elegida; 4:5 se encuadra localmente desde 9:16 con márgenes para conservar la escena y sus subtítulos.
- **Animaciones · gráficos, texto y explicaciones:** Hermes carga manim-video y produce una explicación con Manim. Es apropiado para números, diagramas y demostraciones.
- **Con mis fotos · mostrar mi marca:** aparece cuando hay fotos originales adjuntas; Hermes las usa con textos y animación de apoyo.

La selección se guarda en `answers.video_mode` y controla la ruta incluso si el pedido dice «short». Se puede responder con botones, `clips`, `animaciones` o `mis fotos`; una revisión explícita puede cambiarla. «Un short de 20 segundos sobre mi cafetería» pregunta la dirección; «un short animado con gráficos de 20 segundos» ya la define. Si el usuario delega expresamente la dirección, se puede proponer una sin repetir la pregunta. Las producciones antiguas sin esta clave conservan su ruta anterior.

Shorts y reels se encuadran en 9:16 salvo que el usuario pida otra proporción. El montaje puede desviarse de la duración al sintetizar la voz: diferencias pequeñas se ajustan sincronizando imagen, subtítulos y narración, sin cambiar el tono de voz. El factor admitido es 0,8–1,25; una diferencia mayor se rechaza en lugar de entregar un resultado incompleto.

Para comunicar por qué una marca es buena o diferente, la evaluación pide sus características confirmadas si no están en el contexto. Los clips no sustituyen esos datos. En el montaje con clips, un PDF aporta únicamente su extracto disponible, marcado como lectura parcial; para una explicación detallada de sus páginas conviene el modo animado, que lee el documento con quark-documents.

## Contrato entre repositorios

`GET /api/projects/{id}/brief` conserva el contrato anterior y agrega `question` (clave pendiente o null) y `answered`. `PUT` guarda, cancela o confirma con `id`, `version`, `answers`, `action` y opcionalmente `field` para guardar una respuesta individual. `POST /api/projects/{id}/brief/reply` acepta `id`, `version` y `message` desde el compositor: interpreta opciones, proporciones y cantidades sin llamar al modelo. Confirmar inicia una sola ejecución y devuelve `run`; las claves permanecen en el servidor. `POST /api/projects/{id}/brief/reopen` permite revisar una pieza terminada. La tabla `brief_responses` conserva el avance, sin modificar mensajes o exportaciones anteriores.

Para volver al flujo anterior se pueden revertir los commits de esta implementación en ambos repositorios. La tabla `project_briefs` puede permanecer sin uso; no se borran conversaciones ni exportaciones anteriores.
