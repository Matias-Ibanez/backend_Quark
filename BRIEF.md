# Definir los detalles antes de crear una pieza

El agente evalúa el pedido y los últimos mensajes de la conversación antes de producir una pieza nueva. El formulario «Detalles de la pieza» aparece únicamente si faltan decisiones necesarias, y muestra solo esas preguntas. Si el pedido alcanza, la producción empieza directamente. Las elecciones se guardan por conversación y llegan al agente como contexto estructurado.

## Recorrido

1. Escribí el pedido. Se extraen tema, público, objetivo, formato y preferencias que ya diste; no se vuelven a preguntar por rutina.
2. Completá **Contenido y público**: tema, audiencia y objetivo (informar, vender, explicar o generar interacción).
3. Elegí **Formato y destino**: imagen, video o carrusel; Instagram, TikTok, YouTube, LinkedIn o web; 4:5, 9:16, 1:1 o 16:9. Video admite 5–180 segundos; carrusel, 2–10 láminas.
4. Definí **Identidad visual**: editorial, producto, tipográfica, minimalista o impactante; paleta de marca, neutra, cálida, fría, de contraste o propia; tipografía sans, serif, display o de marca. Podés delegar estas decisiones. Elegí también el tono y si usar los adjuntos.
5. Definí **Texto y revisión**: redacción automática o texto exacto, llamada a la acción, hechos confirmados y restricciones. Al elegir **Usá exactamente mi texto** se abre el campo para escribirlo. Si el agente pide directamente el texto, ese campo ya aparece editable. Para video elegí voz y si vas a agregar música después.
6. Revisá el resumen y pulsá **Confirmar y crear**. Para cambiar opciones después, usá **Modificar formato o estilo de esta pieza**.

Los pasos 2–5 enumeran las opciones disponibles; solo aparecen los campos que el agente considera pendientes. Por ejemplo, «creame una imagen» sin contexto pregunta tema y formato; «creá un reel sobre café» puede preguntar solo duración; una imagen cuadrada con tema y dirección visual puede pasar directamente a producción. Paleta y tipografía pueden decidirse automáticamente. Pedir los colores de una marca sin aportarlos requiere aclararlos. La evaluación depende del modelo y puede equivocarse; se puede cancelar o corregir por chat.

Cada «Guardar y continuar» persiste las respuestas. Los cambios de un paso todavía no guardado no sobreviven a una recarga. Cancelar no genera contenido. Las revisiones por chat conservan el contexto; pedir otra pieza vuelve a evaluar qué falta. El botón para modificar una pieza manualmente conserva el editor completo.

La evaluación estructurada usa DeepSeek sin herramientas y registra tokens y costo en `aux_usage`, con origen `creative_intake`. Un pedido mínimo sin tema ni historial abre las preguntas básicas sin llamar al modelo. Ante un fallo o JSON inválido se muestran tema y formato como respaldo; no se produce a partir de una evaluación inválida.

## Validación y entrega

El backend permite guardar respuestas parciales. Antes de confirmar exige tema y público, colores propios cuando se eligen y contenido para el texto exacto. Valida opciones, longitudes, duración, cantidad de láminas, colores HEX y versiones desactualizadas. Una confirmación solo se consume una vez. Si el servicio se reinicia o la producción falla, las respuestas se conservan para reintentar; un pedido automático sin preguntas previas ofrece un campo de detalles para ajustar el intento.

Los detalles de la pieza no reemplazan las instrucciones del agente. Las fechas, precios y contactos ausentes se omiten. Las fuentes o paletas de marca no disponibles admiten una alternativa coherente; para fijarlas, aportá su nombre y colores propios. Las elecciones estéticas orientan al modelo, pero no garantizan por sí solas calidad visual.

Las imágenes y cada lámina del carrusel conservan SVG y PNG. Un carrusel incompleto no se entrega. Las dimensiones de imagen y video, la duración y la voz solicitada se verifican antes de entregar en el chat. Los shorts con estilo automático, voz y formato 9:16 usan MoneyPrinterTurbo; los demás videos pasan a Hermes para respetar la dirección visual.

## Contrato entre repositorios

`GET /api/projects/{id}/brief` devuelve el estado, grupos y preguntas con sus opciones. `PUT` en esa ruta guarda, cancela o confirma con `id`, `version`, `answers` y `action`. Confirmar inicia una ejecución y devuelve `run`; no se expone ninguna clave al frontend. `POST /api/projects/{id}/brief/reopen` permite revisar un brief terminado. La interfaz está en `landing-quark`; este repositorio conserva la validación, memoria y generación.

Para volver al flujo anterior se pueden revertir los commits de esta implementación en ambos repositorios. La tabla `project_briefs` puede permanecer sin uso; no se borran conversaciones ni exportaciones anteriores.
