# Guía para agentes de IA

Este repo busca ofertas de empleo en varias bolsas y las filtra según un perfil TOML. Tu trabajo es ayudar a la persona a **crear su `profile.toml`**, instalar dependencias, ejecutar la búsqueda y leer los resultados. No necesita saber programar: habla en su idioma, sin jerga técnica, y haz tú los cambios de archivos.

## 1. Entrevista

Pregunta de a pocas preguntas, no todo de golpe. Necesitas:

1. **Profesión y puestos buscados** (ej. "enfermera", "contador senior", "diseñador UX"). Pide 2–4 títulos de puesto, en español y en inglés si busca remoto internacional.
2. **País y ciudad** donde vive o quiere trabajar.
3. **Modalidad**: presencial, híbrido, remoto local o remoto internacional.
4. **Qué descartar**: niveles (practicante, director), áreas cercanas que no le interesan, tecnologías o herramientas que no maneja.
5. **Antigüedad** de las ofertas: por defecto 14 días.
6. (Opcional) **Empresas concretas** donde le gustaría trabajar, para la sección `[boards.ats]`.

## 2. Crear el perfil

Parte del ejemplo más parecido en `profiles/` (`software-dev.toml` tiene todos los campos comentados) y guárdalo como `profile.toml` en la raíz. `profile.toml` está en `.gitignore`: es personal y no se sube.

**`[filters]`**
- `include`: 10–25 palabras que aparezcan en ofertas relevantes, en español e inglés. Usa `*` final para variantes de género o número: `enfermer*`, `contad*`, `diseñador*`.
- `exclude`: palabras que, si están en el **título**, descartan la oferta. Coinciden con palabras completas: `java` no descarta `javascript`.
- `locations`: solo se aplica a bolsas remotas y globales. Incluye su país, región (`latam`, `latin america`, `americas`) y `anywhere`, `worldwide`, `global` si acepta remoto internacional. `[]` acepta cualquier ubicación.

**`[search]`** (LinkedIn, Indeed y Google vía JobSpy)
- `terms`: los títulos de puesto de la entrevista.
- `location`: ciudad o país tal como se escribiría en LinkedIn.
- `country`: país para Indeed, en inglés y minúsculas (`mexico`, `colombia`, `argentina`, `spain`, `usa`, `costa rica`…).
- `remote = true` si solo quiere remoto.

**`[boards]`** — elige fuentes según la profesión:

| Fuente | Úsala cuando |
|---|---|
| `computrabajo` | Casi siempre en LatAm. Configura `computrabajo_country` (subdominio: `mx`, `co`, `ar`, `pe`, `cl`, `ec`, `cr`…) y `computrabajo_queries`. |
| `elempleo` | Vive en Colombia (`co`) o Costa Rica (`cr`). |
| `getonbrd` | Tecnología, diseño, marketing digital o datos en LatAm (solo trae ofertas remotas). |
| `remotive`, `remoteok`, `himalayas` | Busca trabajo remoto. Tienen mucho de tecnología, pero también marketing, ventas, soporte, diseño, finanzas y escritura. |
| `wellfound` | Startups (sobre todo tecnología). |
| `hn` | Solo perfiles de tecnología. |
| `ats` | Hay empresas concretas que le interesan y publican en Greenhouse, Lever o Ashby. |

Para profesiones que no son de tecnología (salud, educación, oficios, comercio, administración), lo más útil suele ser `search.py` y `computrabajo`/`elempleo`. Quita las fuentes que no apliquen en vez de dejarlas todas.

## 3. Instalar

Requiere **Python 3.11 o 3.12** (no 3.13). Comprueba la versión con `python --version` y, si falta, indica cómo instalarla para su sistema operativo.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Verificar y ejecutar

Comprueba que el perfil carga sin errores:

```bash
python -c "from config import load_profile; p = load_profile(); print(p.name, p.boards.sources)"
```

Luego:

```bash
python boards.py     # bolsas remotas, locales y empresas
python search.py     # LinkedIn, Indeed y Google
```

En Windows, si la consola muestra caracteres raros, define `PYTHONIOENCODING=utf-8`.

## 5. Revisar resultados

Los CSV quedan en `results/`. En `boards_*.csv`, `is_new = True` marca las ofertas que no aparecían en búsquedas anteriores. Resume para la persona las más relevantes (título, empresa, ubicación, enlace) en lugar de mostrar el CSV completo.

Si hay **demasiados resultados irrelevantes**, agrega palabras a `exclude` o quita palabras genéricas de `include`. Si hay **muy pocos**, amplía `include`, sube `max_age_days` o agrega fuentes y términos. Ajusta el perfil y vuelve a ejecutar.

## Errores comunes

- `✗ fuente: error`: esa bolsa falló o cambió su web; las demás siguen funcionando. No hace falta arreglarlo para usar la herramienta.
- `No existe el perfil 'profile.toml'`: falta copiar un ejemplo de `profiles/` como `profile.toml`.
- `Fuentes desconocidas`: hay un nombre mal escrito en `[boards].sources`.
- Error instalando NumPy: la versión de Python es 3.13 o superior.
