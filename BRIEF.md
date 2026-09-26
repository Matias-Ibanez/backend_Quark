# Crear una pieza con un brief confirmado

Un pedido como «creame una imagen» abre preguntas en el chat antes de consumir tokens del modelo o renderizar. Las elecciones se guardan por conversación, se recuperan al recargar y llegan al agente como contexto estructurado.

## Recorrido

1. Escribí el pedido. El tema se conserva si ya lo diste; un pedido sin tema exige completarlo.
2. Completá **Contenido y público**: tema, audiencia y objetivo (informar, vender, explicar o generar interacción).
3. Elegí **Formato y destino**: imagen, video o carrusel; Instagram, TikTok, YouTube, LinkedIn o web; 4:5, 9:16, 1:1 o 16:9. Video admite 5–180 segundos; carrusel, 2–10 láminas.
4. Definí **Identidad visual**: editorial, producto, tipográfica, minimalista o impactante; paleta de marca, neutra, cálida, fría, de contraste o propia; tipografía sans, serif, display o de marca. Podés delegar estas decisiones. Elegí también el tono y si usar los adjuntos.
5. Definí **Texto y revisión**: redacción automática o texto exacto, llamada a la acción, hechos confirmados y restricciones. Para video elegí voz y si vas a agregar música después.
6. Revisá el resumen y pulsá **Confirmar y crear**. Para cambiar opciones después, usá **Modificar formato o estilo de esta pieza**.

Cada «Guardar y continuar» persiste las respuestas. Los cambios de un paso todavía no guardado no sobreviven a una recarga. Cancelar no genera contenido. Las revisiones por chat conservan el contexto; pedir otra pieza abre un nuevo brief.

## Validación y entrega

El backend valida opciones, longitudes, duración, cantidad de láminas y colores HEX; rechaza tema o público vacíos, texto exacto vacío y versiones desactualizadas. Una confirmación solo se consume una vez. Si el servicio se reinicia o la producción falla, el brief se conserva para reintentar.

Los datos del brief no reemplazan las instrucciones del agente. Las fechas, precios y contactos ausentes se omiten. Las fuentes o paletas de marca no disponibles admiten una alternativa coherente; para fijarlas, aportá su nombre y colores propios. Las elecciones estéticas orientan al modelo, pero no garantizan por sí solas calidad visual.

Las imágenes y cada lámina del carrusel conservan SVG y PNG. Un carrusel incompleto no se entrega. Las dimensiones de imagen y video, la duración y la voz solicitada se verifican antes de entregar en el chat. Los shorts con estilo automático, voz y formato 9:16 usan MoneyPrinterTurbo; los demás videos pasan a Hermes para respetar la dirección visual.

## Contrato entre repositorios

`GET /api/projects/{id}/brief` devuelve el estado, grupos y preguntas con sus opciones. `PUT` en esa ruta guarda, cancela o confirma con `id`, `version`, `answers` y `action`. Confirmar inicia una ejecución y devuelve `run`; no se expone ninguna clave al frontend. `POST /api/projects/{id}/brief/reopen` permite revisar un brief terminado. La interfaz está en `landing-quark`; este repositorio conserva la validación, memoria y generación.

Para volver al flujo anterior se pueden revertir los commits de esta implementación en ambos repositorios. La tabla `project_briefs` puede permanecer sin uso; no se borran conversaciones ni exportaciones anteriores.
