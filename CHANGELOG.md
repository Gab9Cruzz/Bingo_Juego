# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado semántico.

## [0.1.0] — Fase 1: Cimientos

### Añadido

- Esquema completo de base de datos (SQLite, WAL) con sistema de migraciones
  propio y transaccional.
- Organizaciones: alta, edición, borrado con validación de dependencias, logo
  normalizado a PNG, colores de identidad.
- Eventos en estado `borrador`, asociados a una organización.
- Sistema de idiomas (español/inglés) con retraducción en caliente, sin
  reiniciar la aplicación.
- Ventana principal con dos niveles de navegación: Eventos / Organizaciones /
  Ajustes, y espacio de trabajo por evento.
- Manejo de errores con jerarquía propia, log de aplicación con rotación, y
  diálogo legible ante fallos inesperados.
- Instancia única con detección de bloqueos rancios.
