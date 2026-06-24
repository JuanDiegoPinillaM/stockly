<div align="center">

# 🛍️ Stockly

**Plataforma de comercio e inventario para cualquier negocio.**
Tienda en línea + punto de venta (POS) + control de inventario multi-bodega + analítica, en un solo sistema.

[![Backend](https://img.shields.io/badge/Backend-Django%206%20%2B%20DRF-092E20)](#-stack-técnico)
[![Frontend](https://img.shields.io/badge/Frontend-Vue%203%20%2B%20Vite%206-42b883)](#-stack-técnico)
[![DB](https://img.shields.io/badge/DB-PostgreSQL%2016-336791)](#1-base-de-datos-postgresql-con-docker)
[![Auth](https://img.shields.io/badge/Auth-JWT-orange)](#api-rest)

</div>

---

## 📑 Tabla de contenido

- [¿Qué es Stockly?](#-qué-es-stockly)
- [Funcionalidades](#-funcionalidades)
- [Stack técnico](#-stack-técnico)
- [Arquitectura del proyecto](#️-arquitectura-del-proyecto)
- [Conceptos y decisiones de diseño](#-conceptos-y-decisiones-de-diseño)
- [Puesta en marcha](#-puesta-en-marcha)
- [API REST](#api-rest)
- [Roles y permisos](#-roles-y-permisos)
- [Pruebas y calidad](#-pruebas-y-calidad)

---

## 🎯 ¿Qué es Stockly?

Stockly es un sistema integral pensado para **cualquier tipo de negocio** (ropa,
tecnología, alimentos, etc.) que une tres mundos que normalmente viven en
herramientas separadas:

1. **Tienda en línea (e-commerce)** — catálogo público, carrito, favoritos,
   checkout y seguimiento de pedidos para los compradores.
2. **Punto de venta (POS)** — ventas de mostrador con pago dividido, IVA y
   recibo, que descuentan inventario en tiempo real.
3. **Back-office** — catálogo, inventario multi-bodega con kardex valorizado,
   gestión de pedidos y un **panel de analítica** con KPIs, gráficas y reportes.

Todo se apoya en un modelo de datos donde **clientes y usuarios son la misma
entidad**, **nada se borra** (todo queda como registro histórico) y el costo del
inventario se calcula con **promedio ponderado real**.

---

## ✨ Funcionalidades

### 🗂️ Catálogo y variantes
- Categorías → subcategorías → productos, con marcas.
- **Variantes con atributos flexibles por producto** (estilo Shopify): un
  producto puede variar por Color, Talla, Almacenamiento, RAM… los que necesites.
- **Catálogo de atributos reutilizable** (`AttributeDefinition` / `AttributeOption`):
  defines una vez "Color", "Talla", "Almacenamiento"… y los reutilizas en cualquier
  producto.
- **Fotos por eje visual** (normalmente el color): las imágenes dependen del color,
  no de cada variante, así agregar una talla nueva no obliga a recargar fotos.
- Edición de producto estilo Shopify: guardado híbrido (un solo botón "Guardar"
  para datos generales y variantes), reactivación de variantes desactivadas y
  edición de su combinación.

### 📦 Inventario multi-bodega
- Bodegas / puntos de venta.
- Existencias por bodega y **kardex** (`StockMovement`) con entradas, salidas,
  ajustes y motivos.
- **Costo promedio ponderado real** como verdad del inventario (el costo de
  referencia es solo informativo).
- **Transferencias entre bodegas con aprobación**.
- Módulo de existencias **valorizado**.

### 🧾 Punto de venta (POS)
- Ventas con **pago dividido** (efectivo, tarjeta, transferencia…), IVA y descuento.
- Descuenta inventario creando movimientos de salida (trazabilidad total).
- Búsqueda de cliente por **número de identificación**; **recibo por correo**.
- Anulación de ventas (devuelve existencias).

### 🛒 Tienda en línea (e-commerce)
- Catálogo público con **filtros coherentes por categoría**: marca, **rango de
  precio con slider**, **atributos de variación** (Color, Talla, Almacenamiento…)
  y disponibilidad; ordenamiento por precio/novedad/más vendidos.
- **Una tarjeta por color** (estándar en moda): cada color con su foto y precio;
  segunda foto al pasar el cursor, badges "Nuevo"/"Agotado" y **favoritos**.
- Detalle de producto premium: selección de variantes en **cascada coherente**
  (el color filtra las tallas disponibles), galería por color, zoom y lightbox.
- **Carrito persistido por cuenta** (en la base de datos): invitado en el navegador,
  se **fusiona al iniciar sesión**, revalida stock real al pagar.
- **Lista de favoritos persistida por cuenta**, con contador en la barra de navegación.
- **Checkout** eligiendo punto (envío a domicilio o recoger en tienda), pago
  simulado y direcciones relacionales **país → departamento → ciudad**
  (datos propios DIVIPOLA de Colombia).
- **Pedidos con ciclo de vida**: pendiente → confirmado → enviado → entregado
  (o cancelado), con correo de confirmación y gestión desde el back-office.

### 👤 Cuenta del comprador
- Perfil con **editor de foto** (recorte/encuadre), identificación obligatoria,
  cambio de correo (con re-verificación) y cambio de contraseña.
- Direcciones y métodos de pago guardados.
- **Historial unificado** de compras (pedidos en línea + ventas del POS).

### 📊 Analítica y reportes (panel de inicio)
- **KPIs** con comparación vs. periodo anterior: ingresos, ganancia, transacciones,
  ticket promedio, unidades y clientes.
- **Gráficas propias en SVG** (sin librerías externas): área interactiva con
  tooltip, barras, dona y sparklines.
- Top de productos y categorías, ventas por canal (POS vs. línea), métodos de
  pago, embudo de pedidos e inventario (valor, bajo stock, agotados).
- Filtro por **periodo** (7/30/90 días, 12 meses) y por **bodega**.
- **Exportación de reportes a CSV** (ventas, pedidos, productos, inventario).

### 🔐 Cuentas y seguridad
- Autenticación **JWT** (access + refresh con blacklist al cerrar sesión).
- **Login por correo** (sin username). El correo es opcional para clientes de
  mostrador.
- Registro con **verificación de correo** y restablecimiento de contraseña.
- **Roles** (admin, jefe de punto, cajero, comprador) con permisos por área.

---

## 🧱 Stack técnico

| Capa | Tecnologías |
| ---- | ----------- |
| **Backend** | Django 6 · Django REST Framework · SimpleJWT · drf-spectacular (OpenAPI) · django-filter · django-cors-headers · Pillow |
| **Base de datos** | PostgreSQL 16 (Docker) · `psycopg` 3 |
| **Frontend** | Vue 3 (`<script setup>`) · Vite 6 · Vue Router · Pinia · Axios · lucide-vue-next · SweetAlert2 |
| **Gráficas** | Componentes SVG propios (sin dependencias) |
| **Calidad** | ESLint 9 (flat config) · Prettier · Vitest · pruebas con `manage.py test` |
| **Idioma / Zona** | `es-co` · `America/Bogota` |

---

## 🏗️ Arquitectura del proyecto

```
stockly/
├── backend/                  → API REST (Django + DRF)
│   ├── config/               → settings, urls, wsgi
│   ├── accounts/             → usuarios (login por correo), roles, JWT, perfil
│   ├── catalog/              → categorías, productos, variantes, atributos, marcas
│   ├── inventory/            → bodegas, existencias, kardex, transferencias
│   ├── sales/                → punto de venta (ventas, pagos, recibos)
│   ├── store/                → tienda pública, carrito, favoritos, pedidos, cuenta
│   ├── geo/                  → país → departamento → ciudad (DIVIPOLA Colombia)
│   └── api/                  → health-check + analítica (overview + export CSV)
├── frontend/                 → SPA (Vue 3 + Vite)
│   └── src/
│       ├── views/store/      → tienda pública y área de cuenta
│       ├── views/dashboard/  → back-office (catálogo, inventario, POS, analítica)
│       ├── views/auth/       → login, registro, verificación, reset
│       ├── components/       → UI reutilizable (charts/, store/, AvatarField, etc.)
│       ├── stores/           → Pinia (auth, cart, wishlist)
│       └── services/         → cliente axios por dominio
└── docker-compose.yml        → PostgreSQL 16 para desarrollo
```

---

## 🧠 Conceptos y decisiones de diseño

- **Nada se borra (soft-delete):** los registros se **inactivan**, nunca se
  eliminan; todo queda como histórico e integridad referencial.
- **Clientes = usuarios:** una sola tabla `User`. La identificación (CC/CE/NIT…)
  es la llave de búsqueda del cliente en el POS; el correo es opcional.
- **Costo en 3 niveles:** `cost_price` (referencia) y **`average_cost`** (promedio
  ponderado real, la verdad para valorar inventario y margen).
- **Variantes = atributos N flexibles** por producto, alimentados por un **catálogo
  global** de atributos reutilizables; las fotos cuelgan del **eje visual** (color).
- **Geo propio:** la ubicación (país/departamento/ciudad) vive en la base de datos
  (DIVIPOLA), sin depender de APIs externas en tiempo de ejecución.
- **Carrito y favoritos por cuenta:** persistidos en la BD para usuarios con
  sesión (te siguen entre dispositivos); en localStorage para invitados, con
  **fusión al iniciar sesión**.

---

## 🚀 Puesta en marcha

> Requisitos: **Docker**, **Python 3.10+** y **Node 20+** (recomendado 22).

### 1. Base de datos (PostgreSQL con Docker)

```bash
docker compose up -d     # levanta PostgreSQL en localhost:5433
docker compose down      # detiene (los datos persisten en el volumen)
```

> Se usa el puerto **5433** en el host para no chocar con un PostgreSQL local en
> el 5432. Credenciales y variables en `.env` (raíz) y `backend/.env`.

### 2. Backend (Django)

```bash
cd backend
python -m venv venv
venv\Scripts\activate                 # PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser      # crea un usuario con rol admin
python manage.py runserver            # API en http://localhost:8000
```

> Las variables sensibles se leen de `backend/.env` (ver `backend/.env.example`).
> Los correos se envían por SMTP (Gmail); si no hay credenciales
> (`EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD`), se imprimen por consola.

### 3. Frontend (Vue)

```bash
cd frontend
npm install      # solo la primera vez
npm run dev      # http://localhost:5173
npm run build    # build de producción en dist/
npm run lint     # ESLint
```

> `vite.config.js` proxea `/api` y `/media` hacia Django; el manejo de tokens
> (con refresh automático) está en `src/services/api.js` + `src/stores/auth.js`.

### Flujo completo de desarrollo

```bash
docker compose up -d                                                  # 1. PostgreSQL
cd backend  && venv\Scripts\activate && python manage.py runserver    # 2. API
cd frontend && npm run dev                                            # 3. Frontend
```

---

## API REST

Todos los endpoints están versionados bajo **`/api/v1/`**. Documentación
interactiva generada con drf-spectacular:

- **Swagger UI** → http://localhost:8000/api/docs/
- **Redoc** → http://localhost:8000/api/redoc/
- **Esquema OpenAPI** → http://localhost:8000/api/schema/

### Grupos principales

| Área | Prefijo(s) | Qué incluye |
| ---- | ---------- | ----------- |
| **Auth** | `/auth/…`, `/auth/me/` | registro, login, refresh, logout, verificación de correo, reset, perfil |
| **Catálogo** | `/categories/`, `/subcategories/`, `/products/`, `/variants/`, `/product-attributes/`, `/attribute-values/`, `/attribute-definitions/`, `/attribute-options/`, `/product-images/`, `/brands/` | CRUD del catálogo, variantes y atributos |
| **Inventario** | `/warehouses/`, `/stock/`, `/movements/`, `/transfers/` | bodegas, existencias, kardex y transferencias |
| **Ventas (POS)** | `/sales/…` | ventas, pagos, anulación y recibo |
| **Tienda** | `/store/products/`, `/store/categories/`, `/store/brands/`, `/store/attribute-filters/`, `/store/price-range/`, `/store/points/` | catálogo público y filtros |
| **Cuenta** | `/account/cart/`, `/account/favorites/`, `/account/addresses/`, `/account/payment-methods/`, `/account/orders/`, `/account/purchases/` | carrito, favoritos, direcciones, pedidos, historial |
| **Pedidos (staff)** | `/orders/` | gestión de pedidos en el back-office |
| **Geo** | `/geo/countries/`, `/geo/departments/`, `/geo/cities/` | país → departamento → ciudad |
| **Analítica** | `/analytics/overview/`, `/analytics/export/` | KPIs, series y reportes CSV |

### Autenticación (resumen)

| Método | Endpoint | Descripción |
| ------ | -------- | ----------- |
| POST | `/api/v1/auth/register/` | Crea una cuenta (rol `comprador`) y envía verificación |
| POST | `/api/v1/auth/login/` | Devuelve `access`, `refresh` y datos del usuario |
| POST | `/api/v1/auth/logout/` | Invalida el refresh token (blacklist) |
| POST | `/api/v1/auth/refresh/` | Renueva el `access` token |
| GET  | `/api/v1/auth/me/` | Datos del usuario autenticado (protegido) |
| POST | `/api/v1/auth/verify-email/` | Activa la cuenta con `uid` + `token` |
| POST | `/api/v1/auth/password-reset/` | Envía el correo para restablecer contraseña |

---

## 🔐 Roles y permisos

| Rol | Acceso |
| --- | ------ |
| **admin** | Todo el back-office: catálogo, inventario, transferencias, POS, pedidos y analítica (todas las bodegas). |
| **jefe_punto** | Back-office acotado a su bodega; aprueba transferencias; ve su analítica. |
| **cajero** | POS y pedidos de su bodega. |
| **comprador** | Tienda pública y su área de cuenta (no entra al dashboard). |

El registro público crea siempre **comprador**; `createsuperuser` crea **admin**.
La cuenta queda inactiva hasta verificar el correo.

---

## ✅ Pruebas y calidad

```bash
# Backend (Django)
cd backend && venv\Scripts\activate
python manage.py test          # toda la suite
python manage.py test store    # una app

# Frontend (Vue)
cd frontend
npm run lint                   # ESLint
npm run build                  # verifica el build de producción
```

El proyecto mantiene una suite amplia de pruebas en el backend (catálogo,
ventas, tienda, geo, inventario y analítica) y el frontend pasa `lint` + `build`
limpios en cada cambio.

---

<div align="center">
<sub>Hecho con cuidado al detalle · Django · Vue · PostgreSQL</sub>
</div>
