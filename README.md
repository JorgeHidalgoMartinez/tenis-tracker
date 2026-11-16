# Tenis Tracker

Buscador personal de torneos de tenis absoluto en Madrid y alrededores.

**Web:** https://jorgehidalgomartinez.github.io/tenis-tracker/

## Estado comprobado · 15/11/2026

La web contiene una revisión manual de **8 fichas reales** en un navegador sin
iniciar sesión. Cada registro conserva la hora de revisión y el enlace directo.
No son ejemplos ni una actualización automática: `generationMode` indica
`revision_manual_navegador`.

GitHub Actions devuelve **HTTP 403 incluso con Chromium estándar y entrada por
la portada**. La actualización diaria está configurada, pero todavía no consigue
leer FTM desde ese entorno. Conserva la revisión manual y publica el diagnóstico.
RFET sí responde como directorio. La navegación pública funciona desde el
navegador usado para esta revisión; eso no garantiza acceso desde GitHub.

## Datos y cobertura

La web carga `data/torneos.json`, que solo se sustituye si una consulta real de
FTM produce registros identificables. El resultado del último intento se guarda
separadamente en `data/sync-status.json`. Una respuesta vacía, un error de acceso
o un cambio de formato no se presentan como actualización correcta.

El lector abre el calendario público AVANZA en Chromium estándar, sin iniciar
sesión. Comprueba el mes anterior, el actual y el siguiente, y revisa las fichas
con ABSOLUTO en el título, hasta un máximo de 20. Incluye títulos mixtos
absoluto/veteranos y masculino/femenino; excluye equipos, dobles y otros deportes.
La modalidad individual masculina solo se confirma cuando aparece explícitamente
en «Pruebas y cuadros».

La dirección administrativa del club no se considera sede de juego. La ubicación
solo se recoge cuando la ficha declara expresamente la sede. Las distancias no
se calculan sin coordenadas fiables. Un aviso de suspensión de una jornada no
supone que se haya cancelado todo el torneo.

Los plazos de inscripción se comparan con la hora de Madrid. Una inscripción
abierta no demuestra plazas disponibles. RFET se consulta como directorio de
calendarios territoriales: **no se importa todo su calendario nacional**.

## Automatización

`.github/workflows/sync.yml` se ejecuta a las **07:15 UTC** cada día (08:15 en
invierno y 09:15 en verano en Madrid), al subir a `main` y manualmente desde
Actions. Instala dependencias y Chromium, ejecuta las pruebas, consulta las fuentes,
guarda el resultado y publica los archivos de la aplicación mediante Pages.

Si falla FTM, publica el diagnóstico y conserva la última instantánea válida.
Actions termina con error para que el fallo federativo sea visible. El despliegue
puede haberse completado correctamente aunque la ejecución termine en error.

El HTML inicial de AVANZA no contiene los torneos; se cargan con JavaScript.
La consulta HTTP directa del endpoint devolvió 403 durante la revisión. El lector
actual utiliza la navegación pública normal, sin modificar la huella del navegador,
introducir proxies, usar cuentas ni eludir controles de acceso.

## Uso personal y privacidad

Se conservan hechos mínimos del torneo y enlaces oficiales. No se importan
jugadores, resultados individuales, contactos, fotos ni cuadros. Los favoritos
se guardan en el navegador y no se sincronizan entre dispositivos. No se realizan
inscripciones.

Las condiciones de FTM reservan derechos sobre la reutilización de sus contenidos.
La comprobación técnica no es una autorización general para redistribuir su base
de datos. El proyecto está destinado a uso personal y no publica textos completos
ni su base de datos íntegra.

La instantánea original del ZIP permanece en
`docs/instantanea_original_no_revalidada.json`, como referencia **no revalidada**,
fuera del sitio publicado. Los ejemplos sintéticos existen únicamente en tests.

## Desarrollo

```bash
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium
python -m unittest discover -s tests -v
python scripts/sync_torneos.py --dry-run
python scripts/sync_torneos.py
python scripts/build.py
```

## Fuentes

- https://competicion.ftm.es/app/calendario/mensual
- Ficha pública de cada torneo enlazada desde el calendario.
- https://www.rfet.es/es/calendarios.html
- https://competicion.ftm.es/app/seguridad/condiciones

## Límites

Cobertura parcial por meses y denominación del torneo; puede omitir eventos con
nombres genéricos. Las sedes y modalidades no demostradas quedan pendientes.
La extracción depende del HTML de un tercero y puede fallar si cambia o restringe
el acceso. La programación de Actions no garantiza una hora exacta; GitHub puede
desactivar las programaciones de repositorios públicos tras 60 días sin actividad.


## Seguimiento de Jorge (16/11/2026)

Inicio con ficha RFET verificada por licencia, ranking nacional/territorial, puntos, fecha de cierre e historial de cierres. Mis torneos conserva inscripciones y partidos; Rival compara clasificaciones del mismo cierre y los enfrentamientos cargados; Buscar torneos conserva el buscador anterior.

El perfil deportivo público contiene únicamente nombre, licencia, club y clasificación pública (`data/player-public.json`). Octubre 2026 v1 se verificó en el portal oficial: nacional 5384, territorial 850, 61 puntos, cierre 31/10/2026, publicación 10/11/2026. Es una consulta manual fechada, no un ranking consultado en directo. El sincronizador de torneos no actualiza todavía esta ficha.

Inscripciones, resultados importados y notas se conservan en `localStorage` del navegador. No hay autenticación, cifrado de esas notas ni sincronización entre dispositivos; no equivale a una cuenta privada. Exportar/importar el perfil permite trasladarlo. No subir copias personales al repositorio. Los favoritos y los torneos anotados por el usuario no acreditan una inscripción. La importación se valida y requiere revisar el resumen antes de sustituir la copia local.

Los partidos pasados no aparecen como próximos y los torneos finalizados o retirados se excluyen de la agenda futura. Marcadores desde Jorge; cualquier anotación manual se distingue de una fuente oficial. Comparar rankings no produce probabilidades de victoria ni inferencias sobre la técnica del rival.

Construcción: `python scripts/build.py` incrusta `personal.js`, `personal.css` y el perfil público en `index.html`; el despliegue existente sigue publicando el mismo HTML autónomo. Pruebas: `python -m unittest discover -s tests -v` y `node test-personal.cjs`.
