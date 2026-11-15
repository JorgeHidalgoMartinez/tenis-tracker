# Tenis Tracker

Buscador de torneos de tenis absoluto para Madrid y alrededores, a partir del proyecto Tenis Tracker v2.

**Web:** https://jorgehidalgomartinez.github.io/tenis-tracker/

## Qué muestra

- Búsqueda, filtros, favoritos en este navegador, importación JSON y exportación CSV.
- Solo datos obtenidos mediante consultas reales. La instantánea antigua del ZIP se conserva en `docs/instantanea_original_no_revalidada.json` como referencia **no revalidada**, fuera de la web publicada.
- La fecha de obtención y el resultado del último intento son independientes. Un fallo nunca cambia la fecha del catálogo ni se anuncia como actualización correcta.

## Sincronización

`.github/workflows/sync.yml` se ejecuta diariamente a las **07:15 UTC** (08:15 en invierno / 09:15 en verano en Madrid), al subir código a `main` y manualmente desde Actions.

1. Instala las dependencias y ejecuta las pruebas.
2. Consulta el buscador público FTM/AVANZA mediante la ruta y los parámetros que utiliza el JavaScript público del portal. No usa credenciales ni consultas a jugadores.
3. Consulta RFET como directorio de calendarios territoriales. **No importa ni afirma cubrir el calendario nacional RFET.**
4. Guarda el catálogo solo si obtiene torneos identificables. Guarda el estado de la consulta, también cuando falla.
5. Publica únicamente la aplicación, los iconos y los JSON mediante GitHub Pages con Actions. El fallo de extracción se muestra en la web y hace fallar la ejecución tras publicar el diagnóstico.

El endpoint de AVANZA **no es una API pública documentada ni un contrato estable**. La consulta está limitada a la primera página del buscador (hasta 10 resultados, nombre ABSOLUTO, inicio desde 21 días antes). Puede omitir torneos de denominación genérica o anteriores, y fallar si cambian el formato o los permisos. No intenta saltar bloqueos ni autenticación. El HTML inicial de AVANZA es una aplicación Angular, y por sí solo no contiene los torneos.

## Verificación de datos

- El título y las fechas deben estar explícitos; se descartan respuestas inesperadas.
- Modalidad individual masculina, sede, superficie, distancia e inscripción se dejan pendientes hasta disponer de evidencia específica. Un resultado publicado no demuestra plazas libres.
- `data/sync-status.json`: resultado del último intento y errores por fuente.
- `data/torneos.json`: última instantánea válida. Si todavía no existe una consulta satisfactoria, permanece vacío y sin fecha de obtención.
- Los ejemplos sintéticos están únicamente en las pruebas; no alimentan el catálogo publicado.

## Desarrollo

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/sync_torneos.py --dry-run
python scripts/sync_torneos.py
python scripts/build.py
```

Los favoritos se guardan en `localStorage` de cada navegador; no se sincronizan entre dispositivos. La web no accede a cuentas federativas, no realiza inscripciones y no consulta horarios ni resultados personales.

## Fuentes

- https://competicion.ftm.es/app/
- https://competicion.ftm.es/app/api/calendario.do — consulta de búsqueda utilizada por el cliente público AVANZA (`busquedaTorneos`).
- https://www.rfet.es/es/calendarios.html

La descarga de las páginas públicas y de su JavaScript permite comprobar la estructura técnica, pero no implica permiso de reutilización ilimitado. Deben respetarse las condiciones de cada fuente y cualquier restricción comunicada por la federación.

## Limitaciones de funcionamiento

Las fuentes pueden bloquear consultas desde centros de datos o cambiar sin aviso. La automatización diaria es un intento programado; no garantiza datos nuevos cada día ni una hora exacta. GitHub puede desactivar programaciones de repositorios públicos tras 60 días sin actividad. Se debe revisar Actions si dejan de aparecer intentos.
