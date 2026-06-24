# Stockly

Software de gestión de inventario para tiendas, rapitiendas y pequeños negocios.
Permite registrar entradas y salidas de productos, controlar el stock y consultar
reportes en tiempo real.

## Estructura

```
stockly/
├── frontend/            → Vue 3 + Vite + Vue Router + Pinia
├── backend/             → Django + DRF + JWT (API REST)
└── docker-compose.yml   → PostgreSQL 16 para desarrollo
```

## 1. Base de datos (PostgreSQL con Docker)

```bash
docker compose up -d     # levanta PostgreSQL en localhost:5433
docker compose down      # detiene (los datos persisten en el volumen)
```

> Se usa el puerto **5433** en el host para no chocar con un PostgreSQL local
> que pueda estar en el 5432. Las credenciales están en `.env` (raíz) y
> `backend/.env`.

## 2. Backend (Django)

Requiere Python 3.10+. La primera vez:

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

### API de autenticación (JWT)

Todos los endpoints están versionados bajo `/api/v1/`.

| Método | Endpoint                              | Descripción                                       |
| ------ | ------------------------------------- | ------------------------------------------------- |
| POST   | `/api/v1/auth/register/`              | Crea una cuenta (rol `user`) y envía verificación |
| POST   | `/api/v1/auth/login/`                 | Devuelve `access`, `refresh` y datos del usuario  |
| POST   | `/api/v1/auth/logout/`                | Invalida el refresh token (blacklist)             |
| POST   | `/api/v1/auth/refresh/`               | Renueva el `access` token                         |
| GET    | `/api/v1/auth/me/`                    | Datos del usuario autenticado (protegido)         |
| POST   | `/api/v1/auth/verify-email/`          | Activa la cuenta con `uid` + `token`              |
| POST   | `/api/v1/auth/resend-verification/`   | Reenvía el correo de activación                   |
| POST   | `/api/v1/auth/password-reset/`        | Envía el correo para restablecer contraseña       |
| POST   | `/api/v1/auth/password-reset/confirm/` | Fija la nueva contraseña con `uid` + `token`     |

**Documentación interactiva (Swagger / OpenAPI):**

- Swagger UI → http://localhost:8000/api/docs/
- Redoc → http://localhost:8000/api/redoc/
- Esquema OpenAPI → http://localhost:8000/api/schema/

**Roles:** `admin` y `user`. El registro público crea siempre `user`; los
superusuarios (`createsuperuser`) obtienen el rol `admin`.

**Verificación de correo:** al registrarse, la cuenta queda inactiva hasta que
el usuario confirma su correo (no puede iniciar sesión antes). Los correos se
envían por SMTP (Gmail). Configura `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD`
(contraseña de aplicación) en `backend/.env`. Si no hay credenciales, los
correos se imprimen por consola (`EMAIL_BACKEND` de consola).

## 3. Frontend (Vue)

Requiere **Node 20+** (recomendado 22, ver `frontend/.nvmrc`). Toolchain:
Vite 6 + Vitest 2 + ESLint 9 (flat config).

```bash
cd frontend
npm install      # solo la primera vez
npm run dev      # http://localhost:5173
npm run build    # build de producción en dist/
```

`vite.config.js` incluye un proxy de `/api` hacia Django, y el manejo de tokens
(con refresh automático) está en `src/services/api.js` + `src/stores/auth.js`.

### Páginas

- **Públicas:** Inicio (`/`), Precios (`/precios`), Sobre nosotros
  (`/sobre-nosotros`), Contacto (`/contacto`).
- **Auth:** Login (`/login`) y Registro (`/register`).
- **Privadas:** Dashboard (`/dashboard`) — layout con sidebar y breadcrumb,
  protegido por guard de ruta. Sin módulos todavía.

## Flujo completo de desarrollo

```bash
docker compose up -d                         # 1. PostgreSQL
cd backend && venv\Scripts\activate && python manage.py runserver   # 2. API
cd frontend && npm run dev                   # 3. Frontend
```
