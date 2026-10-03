# job-scraper

Busca ofertas de empleo en más de diez bolsas a la vez, las filtra según **tu carrera** y guarda un CSV con las nuevas desde la última búsqueda.

Sirve para cualquier profesión: todo lo que se busca (palabras clave, país, bolsas, empresas) vive en un archivo de perfil, no en el código. Incluye perfiles de ejemplo para desarrollo de software, marketing digital y contabilidad/finanzas.

## Fuentes

| Script | Fuente | Tipo |
|---|---|---|
| `search.py` | LinkedIn, Indeed, Google Jobs (vía [JobSpy](https://github.com/speedyapply/JobSpy)) | Generalistas |
| `boards.py` | `remotive`, `remoteok`, `himalayas` | Trabajo remoto |
| | `getonbrd`, `computrabajo`, `elempleo` | Bolsas de LatAm |
| | `wellfound` | Startups |
| | `hn` | Hilo mensual *Who is hiring* de Hacker News (solo tech) |
| | `ats` | Vacantes directas de empresas en Greenhouse, Lever y Ashby |

## Instalación

Requiere **Python 3.11 o 3.12** (JobSpy fija una versión de NumPy sin soporte para 3.13).

```bash
git clone https://github.com/emilioorb/job-scraper.git
cd job-scraper
python -m venv .venv
# Windows: .venv\Scripts\activate    |    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Si solo vas a usar `boards.py`, basta con `pip install requests`.

## Configurar con una IA

Si usas un asistente de código (Claude Code, Codex, Cursor, Copilot, Gemini CLI…), abre la carpeta del repo y pídele:

> Ayúdame a configurar mi perfil de búsqueda de empleo.

El asistente lee [`AGENTS.md`](AGENTS.md), te hace unas preguntas sobre tu carrera y crea `profile.toml`, instala las dependencias y ejecuta la búsqueda por ti.

## Uso

1. Elige el perfil más parecido a tu carrera y cópialo como `profile.toml`:

   ```bash
   cp profiles/marketing.toml profile.toml
   ```

2. Edítalo (ver [Configurar tu perfil](#configurar-tu-perfil)).

3. Ejecuta:

   ```bash
   python boards.py     # bolsas remotas, locales y empresas
   python search.py     # LinkedIn, Indeed y Google
   ```

Los resultados quedan en `results/` como CSV. `boards.py` agrega la columna `is_new`, que marca las ofertas que no aparecían en ningún CSV anterior: así cada búsqueda te muestra solo lo nuevo.

### Opciones útiles

```bash
python boards.py --profile profiles/finanzas.toml       # usar otro perfil sin copiarlo
python boards.py --sources remotive himalayas           # solo algunas fuentes
python search.py --terms "Enfermera" "Nurse" --location "Panamá" --hours 24
python search.py --location "Latin America" --remote    # solo remotas
```

Cualquier flag de `search.py` sobrescribe lo que diga el perfil.

## Configurar tu perfil

El perfil es un archivo [TOML](https://toml.io/es/) con cuatro secciones. `profiles/software-dev.toml` tiene todos los campos comentados.

```toml
[profile]
name = "Diseño UX"

[filters]
include = ["ux", "ui", "diseñador*", "designer", "figma", "product design"]  # al menos una
exclude = ["director", "intern*", "graphic"]                               # descarta por título
locations = ["latam", "anywhere", "worldwide", "colombia"]                 # [] = cualquiera
max_age_days = 14

[search]
terms = ["UX Designer", "Diseñador UX"]
location = "Colombia"
country = "colombia"

[boards]
sources = ["remotive", "himalayas", "getonbrd", "computrabajo"]
getonbrd_queries = ["ux", "ui", "product designer"]
computrabajo_country = "co"
computrabajo_queries = ["diseñador ux", "diseñador ui"]
```

**Reglas de palabras clave**

- No distinguen mayúsculas y coinciden con palabras completas: `java` no coincide con `javascript`.
- Un `*` final las convierte en prefijo: `contad*` coincide con *contador*, *contadora*, *contaduría*.
- `include` se busca en el título y los detalles; `exclude` solo en el título.

**Campos de `[boards]`**

| Campo | Para qué |
|---|---|
| `sources` | Fuentes a consultar. Quita las que no apliquen a tu carrera (p. ej. `hn` y `wellfound` son casi solo tech). |
| `getonbrd_queries` | Búsquedas libres en Get on Board. |
| `computrabajo_country` / `computrabajo_queries` | Subdominio del país (`mx`, `co`, `ar`, `pe`, `cl`, `cr`…) y búsquedas. |
| `elempleo_country` | `co` o `cr`. Solo trae las 50 ofertas más recientes (el buscador requiere sesión). |
| `wellfound_roles` | Slugs de `wellfound.com/role/r/<slug>`. |
| `[boards.ats]` | Empresas por ATS. El slug es el de la URL pública: `boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>`, `jobs.ashbyhq.com/<slug>`. |

Las bolsas locales (`getonbrd`, `computrabajo`, `elempleo`) no se filtran por `locations`, porque ya son de un país o región.

## Limitaciones

- Los sitios cambian su HTML o APIs sin aviso; si una fuente falla, el script lo reporta (`✗ fuente: error`) y sigue con las demás.
- Indeed suele bloquear las descripciones completas y Glassdoor bloquea por completo.
- Respeta los términos de uso de cada sitio: úsalo para búsquedas personales y con moderación.

## Contribuir

Se agradecen perfiles nuevos para otras carreras en `profiles/` y fuentes nuevas en `boards.py`: cada fuente es una función que recibe la configuración y produce objetos `Job`, registrada en `SOURCES`.

## Licencia

[MIT](LICENSE)
