# TechStore U4 · Implementación del Núcleo de Negocio

**Componentes de Lógica de Negocio | Unidad 4 | FIME · UANL**

Este proyecto implementa el núcleo de lógica de negocio para la gestión de pedidos de **TechStore**, aplicando los principios de **Domain-Driven Design (DDD)**, el patrón **Specification**, una **Máquina de Estados Finita** con **Domain Events** y una **API REST** construida con **FastAPI**, acompañada de una suite exhaustiva de pruebas automáticas con **pytest**.

---

## Estructura del Proyecto

```text
Actividad 4/
│
├── app/
│   ├── __init__.py           # Inicialización del paquete app
│   ├── domain.py             # Entidades, Value Objects, Aggregate Root y Domain Events
│   ├── specifications.py     # Patrón Specification y reglas compuestas de descuento
│   └── api.py                # API REST con FastAPI y endpoints de negocio
│
├── datos/
│   ├── clientes.csv          # 12 clientes (identificador, membresía VIP, estatus)
│   ├── productos.csv         # 12 productos del catálogo con precios en MXN
│   ├── pedidos.csv           # 16 pedidos iniciales (todos en estado DRAFT)
│   ├── detalle_pedidos.csv   # 21 renglones de artículos asociados a pedidos
│   └── escenarios.csv        # 15 situaciones de evaluación del negocio (E01 a E15)
│
├── tests/
│   ├── __init__.py           # Inicialización del paquete de pruebas
│   ├── test_domain.py        # Pruebas unitarias del dominio, invariantes y escenarios
│   └── test_api.py           # Pruebas de integración de la API REST (códigos 200, 404, 409, 422)
│
├── cargar_csv.py             # Cargador de fixtures desde CSV a objetos del dominio
├── ejecutar_escenarios.py    # Script ejecutor y generador de la bitácora E01 a E15
├── .gitignore                # Exclusión de entornos virtuales, cachés y temporales
├── README.md                 # Documentación completa del proyecto
└── README.txt                # Reglas didácticas del paquete de alumno
├── docs/
│   ├── evidencias            # Evidencias de la actividad 
|   ├── Fundamental-4.pdf           # Reporte del proyecto 
```

---

## Requisitos y Preparación del Entorno

### Requisitos Previos
- **Python 3.11 o superior** (Desarrollado y probado en Python 3.12.10 x64)

### Instalación Paso a Paso

1. **Creación del entorno virtual:**
   ```bash
   python -m venv .venv
   ```

2. **Activación del entorno virtual:**
   - *Windows (PowerShell):*
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```
   - *Windows (CMD):*
     ```cmd
     .\.venv\Scripts\activate.bat
     ```
   - *Linux / macOS:*
     ```bash
     source .venv/bin/activate
     ```

3. **Instalación de dependencias:**
   ```bash
   pip install fastapi uvicorn pytest httpx python-docx
   ```

---

## Ejecución del Proyecto

### 1. Carga de Fixtures en Memoria
Para verificar la carga de los 16 pedidos en estado inicial `DRAFT`:
```bash
python cargar_csv.py
```
**Salida esperada:**
```text
O001 DRAFT 4 2100.00
O002 DRAFT 2 1050.00
O003 DRAFT 4 2100.00
...
O016 DRAFT 1 2100.00
```

### 2. Ejecución de la Bitácora de Escenarios (E01 – E15)
Para evaluar los 15 casos de prueba de negocio y transiciones:
```bash
python ejecutar_escenarios.py
```

### 3. Ejecución de Pruebas Unitarias y de Integración con Pytest
Para ejecutar toda la suite de pruebas automatizadas:
```bash
python -m pytest -v
```
*(42 pruebas pasando con 100% de éxito).*

### 4. Levantamiento de la API REST con FastAPI
Para iniciar el servidor de desarrollo:
```bash
uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```
- **Documentación Interactiva Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Documentación ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Especificación OpenAPI (JSON):** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## Reglas de Negocio e Invariantes del Dominio

1. **Precisión Monetaria con `Money` (Value Object):**
   - Inmutable (`frozen=True`).
   - Utiliza `Decimal` para evitar errores de coma flotante.
   - Moneda única `MXN`; rechaza sumas entre divisas distintas.
   - Rechaza valores negativos o valores no finitos (`NaN`, `Inf`).

2. **Límite de Unidades Físicas:**
   - Un pedido admite un **máximo estricto de 20 unidades físicas en total**, calculado como la suma de las cantidades (`sum(item.quantity)`), sin importar la cantidad de renglones distintos. Si una adición supera las 20 unidades, se detiene antes de modificar el pedido y lanza `OrderItemLimitExceeded`.

3. **Ciclo de Vida de Pedidos (Máquina de Estados):**
   ```text
      [confirm()]                     [ship(guía)]                    [deliver()]
                         Evento: OrderConfirmed          Evento: OrderShipped           Evento: OrderDelivered
                         ────────────────────>          ──────────────────>           ─────────────────────>
      ● ─> +----------------------+      +----------------------+      +----------------------+      +----------------------+
           | Creado, aún no       |      |     Confirmado      |      |       Enviado       |      ||      Entregado      ||
           | confirmado           |      |     (CONFIRMED)      |      |      (SHIPPED)       |      ||     (DELIVERED)      ||
           | (DRAFT)              |      +----------------------+      +----------------------+      +----------------------+
           +----------------------+                |                             |
                      |                            | [cancel(reason)]            | [return_order()]
                      |                            | Evento: OrderCancelled      | Evento: OrderReturned
                      |                            v                             v
                      |                 +======================+      +======================+
                      |                 ||     Cancelado      ||      ||      Devuelto       ||
                      |                 ||    (CANCELLED)     ||      ||     (RETURNED)      ||
                      |                 +======================+      +======================+
                      |
                      | confirm() inválido
                      | - - - - - - - - - - - - - - - - - - - - - - >
                      |                                           |
                      v                                           v
           +-------------------------------------------------------------+
           |                   OPERACIÓN RECHAZADA                       |
           |-------------------------------------------------------------|
           | • Pedido sin artículos.                                     |
           | • Cliente inactivo.                                         |
           | • Más de 200 unidades.                                      |
           |                                                             |
           | El pedido permanece en DRAFT.                               |
           | No se genera ningún evento.                                 |
           +-------------------------------------------------------------+
   ```
   - **`confirm()`**: Exige que el pedido esté en `DRAFT`, contenga al menos 1 artículo y el cliente esté activo (`active=True`). Emite `OrderConfirmed`.
   - **`ship(tracking_number)`**: Exige estado `CONFIRMED` y número de guía no vacío. Emite `OrderShipped`.
   - **`cancel(reason)`**: Exige estado `CONFIRMED` y motivo de cancelación no vacío. Emite `OrderCancelled`.
   - **`deliver()`**: Exige estado `SHIPPED`. Emite `OrderDelivered`.
   - **`return_order()`**: Exige estado `SHIPPED`. Emite `OrderReturned`.
   - **Atomicidad de Eventos**: Si una regla falla, el estado no se modifica y **NO** se emiten eventos.

4. **Reglas de Descuento con el Patrón Specification:**
   - **Regla del 10%:**
     $$\text{VIP} \land (\text{Total} > 500) \land (\text{Unidades} \ge 4) \land \neg(\text{Tiene Promoción})$$
   - **Regla del 5%:**
     $$(\text{Total} > 5000) \land \neg(\text{Tiene Promoción})$$
   - **Prioridad:** Si ambas reglas se satisfacen simultáneamente, tiene prioridad el **10%**. Si el pedido tiene promoción activa, no califica para ningún descuento.

---

## Endpoints de la API REST

| Método | Ruta | Descripción | Códigos HTTP |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Información general y estado de la API | 200 |
| `POST` | `/reset` | Restablece los pedidos en memoria a partir de los CSV | 200 |
| `GET` | `/orders` | Lista todos los pedidos con unidades, totales y descuentos | 200 |
| `GET` | `/orders/{id}` | Detalle completo de un pedido, sus artículos y eventos | 200, 404 |
| `GET` | `/orders/{id}/discount` | Evaluación de la regla de descuento aplicable | 200, 404 |
| `POST` | `/orders/{id}/confirm` | Confirma un pedido en estado `DRAFT` | 200, 404, 409, 422 |
| `POST` | `/orders/{id}/ship` | Envía un pedido confirmado con guía de rastreo | 200, 404, 409, 422 |
| `POST` | `/orders/{id}/cancel` | Cancela un pedido confirmado indicando el motivo | 200, 404, 409, 422 |
| `POST` | `/orders/{id}/deliver` | Registra la entrega de un pedido enviado | 200, 404, 409, 422 |
| `POST` | `/orders/{id}/return` | Registra la devolución de un pedido enviado | 200, 404, 409, 422 |
| `POST` | `/orders/{id}/items` | Agrega un nuevo artículo a un pedido en `DRAFT` | 200, 404, 409, 422 |

---

## Matriz de Respuestas HTTP

- **200 OK**: Transición o consulta completada satisfactoriamente.
- **404 Not Found**: El pedido solicitado no existe en la base de datos en memoria.
- **409 Conflict**: Violación de la máquina de estados (ej. intentar confirmar un pedido que ya está en `CONFIRMED`, o cancelar un pedido que ya está en `SHIPPED`).
- **422 Unprocessable Entity**: Violación de invariantes de datos (ej. intentar confirmar un pedido sin artículos, con cliente inactivo, enviar sin número de guía o exceder el límite de 20 unidades).
