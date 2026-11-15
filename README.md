# Tenis Tracker

Buscador personal de torneos de tenis absoluto en Madrid y alrededores.

**Web:** https://jorgehidalgomartinez.github.io/tenis-tracker/

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
