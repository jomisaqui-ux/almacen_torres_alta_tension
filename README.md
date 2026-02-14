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

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/TU_USUARIO/almacen_torres_alta_tension.git
   cd almacen_torres_alta_tension