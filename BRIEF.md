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

Las imágenes y cada lámina del carrusel conservan SVG y PNG. Un carrusel incompleto no se entrega. Las dimensiones de imagen y video, la duración y la voz solicitada se verifican antes de entregar en el chat. Los shorts con estilo automático, voz y formato 9:16 usan MoneyPrinterTurbo; los demás videos pasan a Hermes para respetar la dirección visual.

## Contrato entre repositorios

`GET /api/projects/{id}/brief` conserva el contrato anterior y agrega `question` (clave pendiente o null) y `answered`. `PUT` guarda, cancela o confirma con `id`, `version`, `answers`, `action` y opcionalmente `field` para guardar una respuesta individual. `POST /api/projects/{id}/brief/reply` acepta `id`, `version` y `message` desde el compositor: interpreta opciones, proporciones y cantidades sin llamar al modelo. Confirmar inicia una sola ejecución y devuelve `run`; las claves permanecen en el servidor. `POST /api/projects/{id}/brief/reopen` permite revisar una pieza terminada. La tabla `brief_responses` conserva el avance, sin modificar mensajes o exportaciones anteriores.

Para volver al flujo anterior se pueden revertir los commits de esta implementación en ambos repositorios. La tabla `project_briefs` puede permanecer sin uso; no se borran conversaciones ni exportaciones anteriores.
