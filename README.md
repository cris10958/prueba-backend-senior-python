# Prueba Técnica — Backend

**Tiempo estimado:** 1 hora
**Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest, Docker

---

## Contexto

Construye un servicio HTTP que evalúe solicitudes de crédito. Una solicitud incluye:

| Campo               | Tipo  | Descripción                                       |
|---------------------|-------|---------------------------------------------------|
| `amount`            | int   | Monto solicitado en COP                           |
| `monthly_income`    | int   | Ingresos mensuales en COP                         |
| `employment_months` | int   | Antigüedad laboral en meses                       |
| `external_score`    | int   | Score externo (0–1000)                            |
| `product`           | str   | Tipo de producto: `PHONE`, `TWIST` o `CARD`       |

## Reglas de evaluación

Existen tres políticas que se aplican según el tipo de producto:

| Producto | Política     | Regla                                                                 |
|----------|--------------|-----------------------------------------------------------------------|
| PHONE    | Conservadora | `score ≥ 700` AND `employment_months ≥ 12` AND `cuota ≤ 25% ingreso` |
| TWIST    | Estándar     | `score ≥ 600` AND `cuota ≤ 35% ingreso`                              |
| CARD     | Agresiva     | `score ≥ 550` OR (`score ≥ 500` AND `monthly_income ≥ 3,000,000`)    |

> Asume plazo fijo de 12 meses: `cuota = amount / 12`

Cada solicitud debe persistirse con su decisión (`APPROVED` o `REJECTED`) y las razones del rechazo cuando aplique.

## Endpoints requeridos

1. **`POST /applications`** — recibe la solicitud, la evalúa y la persiste. Retorna la decisión.
2. **`GET /applications/{id}`** — retorna una solicitud por ID.
3. **`GET /applications?status=APPROVED&product=TWIST`** — lista con filtros opcionales.

## Restricciones de diseño

- La selección de política según producto **no** debe ser un `if/elif` dentro del endpoint.
- El acceso a la base de datos **no** debe estar acoplado al endpoint.
- Cubre con tests al menos: una aprobación, un rechazo por cada política, y el flujo end-to-end del endpoint.

## Bonus (solo si te sobra tiempo)

`POST /applications/{id}/reevaluate` que vuelva a correr la evaluación con la política actual (útil si cambian umbrales).

---

## Setup

**Requisitos:** Docker Desktop instalado. Nada más.

### Levantar el servicio

```bash
docker compose up --build
```

- API: http://localhost:8000
- Docs interactivos: http://localhost:8000/docs

### Correr los tests

```bash
docker compose run --rm app pytest -v
```

### Estructura sugerida (puedes modificarla si lo justificas)

```
app/
├── main.py              # FastAPI app + routers
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── database.py          # engine + session
├── repositories/        # acceso a datos
├── services/            # orquestación
└── strategies/          # políticas de evaluación
tests/
```

## Entrega

Push a tu repo personal (público, o privado con acceso compartido) y envía el link.

¡Éxitos!

---

# Solución — Decisiones de diseño

## Estructura

```
app/
├── main.py                              # FastAPI app + registro del router
├── enums.py                             # Product, ApplicationStatus
├── exceptions.py                        # excepciones de dominio (sin dependencia de HTTP)
├── models.py                            # modelo SQLAlchemy
├── schemas.py                           # schemas Pydantic (entrada/salida)
├── database.py                          # engine + session (sin cambios)
├── routers/applications.py              # endpoints HTTP
├── services/evaluation_service.py       # orquestación
├── repositories/application_repository.py  # acceso a datos
└── strategies/
    ├── base.py                          # contrato EvaluationPolicy + cálculo de cuota
    ├── policies.py                      # las tres políticas
    └── registry.py                      # mapeo producto -> política
```

Se agregó `routers/` a la estructura sugerida para que `main.py` quede solo con el armado de la
aplicación, y `enums.py` para evitar una importación circular entre `models.py` y `schemas.py`.

## 1. Selección de política sin `if/elif`

Patrón **Estrategia** con un **registro**: `registry.py` tiene un diccionario `Product → política` y
`get_policy()` resuelve cuál aplicar.

Agregar un producto nuevo es agregar una clase en `policies.py` y una entrada en el diccionario.
No se toca el endpoint, ni el servicio, ni el repositorio.

## 2. Acceso a datos desacoplado del endpoint

Tres capas con dependencias hacia adentro:

```
router  →  service  →  repository  →  SQLAlchemy
```

- El **router** solo traduce HTTP: valida con Pydantic y convierte las excepciones de dominio en
  códigos de estado. No conoce la sesión de base de datos.
- El **servicio** orquesta política y persistencia. No sabe nada de HTTP ni de SQLAlchemy, así que
  se puede probar con un doble de prueba.
- El **repositorio** es el único punto que habla con la base de datos.

El armado se hace con `Depends` en `get_service()`, lo que además permite sustituir la base de
datos en los tests con `app.dependency_overrides`.

## 3. Las políticas devuelven razones, no decisiones

`evaluate()` devuelve `list[str]`: una lista vacía significa aprobado.

Así la política solo aporta el juicio técnico y es el servicio quien lo traduce a
`APPROVED`/`REJECTED`. Además, las políticas conjuntivas (PHONE y TWIST) revisan **todas** las
condiciones en vez de cortar en la primera que falla, para poder informar todos los motivos de
rechazo en una sola respuesta.

## 4. `Protocol` en vez de herencia

`CreditRequest` es un `Protocol` (tipado estructural): tanto el schema de entrada
`ApplicationCreate` como el modelo ORM `Application` lo cumplen sin heredar de nada.

Gracias a eso, **la misma política sirve para evaluar una solicitud nueva y para reevaluar una ya
guardada**, y el endpoint de reevaluación no duplica lógica.

## 5. `Decimal` en vez de `float` para la cuota

La relación cuota/ingreso se compara con `Decimal`. Con `float`, el redondeo binario cambia la
decisión en los casos de frontera, y en dinero eso no es aceptable. Hay un test que cubre
justamente el caso límite: cuota exactamente igual al 25 % del ingreso.

## 6. Trazabilidad

Cada solicitud guarda `policy_name` y `evaluated_at`. Si mañana cambian los umbrales, queda
registro de con qué criterio se evaluó cada caso. Esto es lo que le da sentido al endpoint de
reevaluación del bonus.

## 7. Validación en la frontera

Las validaciones de formato (monto positivo, score entre 0 y 1000, producto válido) viven en los
schemas de Pydantic. Las políticas reciben datos que ya se sabe que son válidos y se ocupan solo de
las reglas de negocio.

## 8. Validación defensiva de los montos

Los campos numéricos son estrictos (`strict=True`) y tienen cota superior. Sin lo primero, Pydantic
aceptaría `true` como monto y lo convertiría en `1`; sin lo segundo, un entero mayor que el rango de
`INTEGER` llegaría hasta el `commit()` y la API respondería 500 en lugar de 422. Ambos casos están
cubiertos por tests.

## 9. Marcas de tiempo en UTC explícito

`evaluated_at` se persiste en UTC y se serializa con el desplazamiento incluido. SQLite no almacena
la zona horaria, de modo que sin el serializador el consumidor leería la hora como local, con cinco
horas de diferencia en Colombia.

## Cómo levantarlo y probarlo

```bash
docker compose up --build
```

- API: <http://localhost:8000>
- **Documentación interactiva: <http://localhost:8000/docs>** — permite probar todos los endpoints
  desde el navegador, sin herramientas adicionales.

Para ejecutar las pruebas:

```bash
docker compose run --rm app pytest -v
```

Para detener el servicio y limpiar la base de datos local:

```bash
docker compose down
rm -f credit_eval.db
```

### Ejemplos listos para copiar

**Solicitud aprobada** (PHONE: score 750, 24 meses de antigüedad, cuota del 3,3 % del ingreso)

```bash
curl -X POST http://localhost:8000/applications \
  -H 'Content-Type: application/json' \
  -d '{"amount":1200000,"monthly_income":3000000,"employment_months":24,"external_score":750,"product":"PHONE"}'
```

**Solicitud rechazada por los tres motivos** (PHONE)

```bash
curl -X POST http://localhost:8000/applications \
  -H 'Content-Type: application/json' \
  -d '{"amount":9000000,"monthly_income":2000000,"employment_months":2,"external_score":500,"product":"PHONE"}'
```

```json
{
  "status": "REJECTED",
  "rejection_reasons": [
    "El score crediticio (500) es inferior al mínimo requerido (700).",
    "La antigüedad laboral (2 meses) es inferior al mínimo requerido (12 meses).",
    "La cuota mensual ($750.000,00) supera el 25% de los ingresos mensuales ($500.000,00)."
  ],
  "policy_name": "CONSERVATIVE"
}
```

**CARD aprobada por la ruta alternativa** (score 500, insuficiente por sí solo, con ingreso de 3.000.000)

```bash
curl -X POST http://localhost:8000/applications \
  -H 'Content-Type: application/json' \
  -d '{"amount":5000000,"monthly_income":3000000,"employment_months":0,"external_score":500,"product":"CARD"}'
```

**Consulta, listado con filtros y reevaluación**

```bash
curl http://localhost:8000/applications/1
curl 'http://localhost:8000/applications?status=REJECTED'
curl 'http://localhost:8000/applications?status=APPROVED&product=PHONE'
curl -X POST http://localhost:8000/applications/1/reevaluate
```

### Casos de frontera que vale la pena revisar

| Caso | Entrada | Resultado esperado |
|---|---|---|
| Límite exacto aprueba | `score=700`, `employment_months=12`, `amount=6000000`, `income=2000000` (PHONE) | `APPROVED` |
| Cuota al 35 % exacto | `amount=5505045`, `income=1310725`, `score=600` (TWIST) | `APPROVED` (con `float` sería rechazada) |
| Monto fuera de rango | `amount=9223372036854775808` | `422`, no `500` |
| Booleano como monto | `amount=true` | `422` |
| Producto inexistente | `product="LAPTOP"` | `422` |
| Solicitud inexistente | `GET /applications/9999` | `404` |

## Tests

**38 tests**, divididos en dos niveles:

- `tests/test_policies.py` — unitarios, sin API ni base de datos. Cubren una aprobación y cada
  motivo de rechazo de las tres políticas, la acumulación de varios motivos, los casos de frontera
  (score exactamente 700, cuota exactamente en el límite) y la ruta alternativa de CARD.
- `tests/test_applications_api.py` — de punta a punta sobre la API: creación aprobada y rechazada,
  consulta por id, 404, los filtros combinados del listado, entradas inválidas y reevaluación.

Incluye tests de regresión para los casos de frontera que motivaron decisiones de diseño: el
límite exacto de cuota que `float` rechazaría, los montos fuera del rango almacenable, el booleano
como monto, y la actualización de la marca de tiempo al reevaluar.

El `conftest.py` levanta una SQLite **en memoria** por test con `StaticPool` y sustituye `get_db`
con `dependency_overrides`, de modo que los tests quedan aislados entre sí y no tocan el archivo de
base de datos real.

## Bonus implementado

`POST /applications/{id}/reevaluate` vuelve a aplicar la política vigente sobre una solicitud ya
guardada y actualiza decisión, razones, política y marca de tiempo.

## Qué haría distinto en producción

- **Alembic** para migraciones, en vez de `create_all` al arrancar.
- **PostgreSQL** en lugar de SQLite, con índices en `status` y `product` para el listado.
- **Paginación** en `GET /applications`: hoy devuelve todo, lo que no escala.
- **Razones como códigos** (`SCORE_BELOW_MINIMUM`) además del mensaje en español, para que el
  consumidor pueda reaccionar sin interpretar cadenas y para separar la presentación de la lógica.
- **Umbrales configurables** (base de datos o configuración) en vez de constantes de clase, con
  versionado de políticas, para poder ajustar el riesgo sin desplegar.
- **Observabilidad**: logs estructurados con id de correlación, métricas de tasa de aprobación por
  producto y trazas distribuidas.
- **Autenticación y autorización**: hoy cualquiera puede crear y reevaluar solicitudes.
- **Idempotencia** en `POST /applications` mediante una clave de idempotencia, para que un reintento
  de red no duplique la solicitud.
- **Control de concurrencia** en la reevaluación: hoy es un leer-modificar-escribir sin bloqueo ni
  versión optimista.
- **Imagen de producción**: el `Dockerfile` corre como root y con `--reload`, lo que sirve para la
  prueba pero no para desplegar.
- **Escaneo de dependencias** en el pipeline (por ejemplo `pip-audit`), con las versiones fijadas.
