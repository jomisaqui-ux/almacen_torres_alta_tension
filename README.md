# Sistema de Gestión de Almacén de Obra (ERP)

Sistema integral desarrollado en Django para el control logístico, gestión de activos y kardex valorizado en proyectos de construcción.

## 🚀 Módulos Principales

### 📦 Logística y Almacén
- **Kardex Valorizado:** Cálculo automático de PMP (Precio Medio Ponderado).
- **Control de Stock:** Semáforos de alerta (Crítico, Advertencia, OK).
- **Movimientos:** Ingresos (Compras, Devoluciones) y Salidas (Consumo Torre, EPP).
- **Requerimientos:** Gestión de pedidos de obra con estados (Pendiente, Parcial, Total).
- **Reportes:** Exportación a Excel y generación de Vales en PDF con códigos QR.

### 🛠 Gestión de Activos
- **Inventario de Herramientas:** Control de activos fijos y equipos.
- **Kits:** Creación de kits de herramientas para asignación masiva.
- **Asignaciones:** Préstamo y devolución de activos a trabajadores.

### 👷 Recursos Humanos (Básico)
- Gestión de trabajadores para asignación de EPPs y Activos.
- Control de tallas (Ropa, Zapatos).

## 🛠 Tecnologías

- **Backend:** Python 3.12, Django 5.0
- **Base de Datos:** PostgreSQL
- **Frontend:** Bootstrap 5, Crispy Forms
- **Utilitarios:** 
  - `xhtml2pdf`: Generación de Vales PDF.
  - `openpyxl`: Reportes Excel.
  - `qrcode`: Trazabilidad documental.

## ⚙️ Instalación Local

### 1. Clonar el repositorio
```bash
git clone https://github.com/TU_USUARIO/almacen_torres_alta_tension.git
cd almacen_torres_alta_tension
```

### 2. Crear y activar entorno virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configuración de Base de Datos (PostgreSQL)
Accede a tu consola de PostgreSQL (`psql` o pgAdmin) y ejecuta los siguientes comandos SQL para preparar el entorno:

```sql
-- 1. Crear la base de datos
CREATE DATABASE almacen_obra_db;

-- 2. Crear usuario y contraseña (evita usar 'postgres' por seguridad)
CREATE USER admin_almacen WITH PASSWORD 'segura123';

-- 3. Otorgar privilegios
GRANT ALL PRIVILEGES ON DATABASE almacen_obra_db TO admin_almacen;

-- (Nota: En PostgreSQL 15+ es necesario otorgar permisos en el esquema public)
-- \c almacen_obra_db
-- GRANT ALL ON SCHEMA public TO admin_almacen;
```

### 5. Variables de Entorno (.env)
Crea un archivo llamado `.env` en la raíz del proyecto (al mismo nivel que `manage.py`) con el siguiente contenido:

```ini
DEBUG=True
SECRET_KEY=tu_clave_secreta_super_segura
ALLOWED_HOSTS=localhost,127.0.0.1

# Configuración de Base de Datos
# Formato: postgres://USUARIO:PASSWORD@HOST:PUERTO/NOMBRE_DB
DATABASE_URL=postgres://admin_almacen:segura123@localhost:5432/almacen_obra_db
```

### 6. Inicializar el sistema
Una vez configurada la base de datos y el archivo .env, ejecuta las migraciones:

```bash
python manage.py migrate
```

### 7. Crear Superusuario (Administrador)
Para acceder al panel de administración y gestión total:

```bash
python manage.py createsuperuser
```

### 8. Ejecutar el servidor
```bash
python manage.py runserver
```

Visita `http://127.0.0.1:8000/` en tu navegador.