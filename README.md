# MAHEBEER - Recetas y Costos

Aplicación de escritorio para Windows/PC con tema oscuro, SQLite local, copias de seguridad automáticas, recetas, costos, simulación por actualización de ingredientes, reportes y exportación a Excel/PDF.

## Ejecutar en desarrollo

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .
python -m mahebeer.app
```

## Funciones principales

- Ingredientes con costo de compra, cantidad comprada, tipo de medida y costo unitario automático.
- Recetas con buscador de ingredientes, cantidades usadas, costo total y costo por porción.
- Precio sugerido por margen, precio manual, ganancia, margen bruto y rentabilidad.
- Reportes de ingredientes costosos, costo promedio, inventario e historial.
- Papelera lógica, duplicado/copiado de recetas, importación Excel y exportación Excel/PDF.
- Base local SQLite en `Documentos/MAHEBEER` con backups rotativos.
