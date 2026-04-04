# 📝 NotepadX Pro 2.0

> Editor de código con características de IDE — construido en Python con PyQt6 y QScintilla.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.x-41CD52?style=flat-square)
![QScintilla](https://img.shields.io/badge/QScintilla-2.x-blue?style=flat-square)
![Theme](https://img.shields.io/badge/Theme-Catppuccin%20Mocha-CBA6F7?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---

## ¿Qué es?

NotepadX Pro es un editor de texto orientado a código con características propias de un IDE, construido completamente en Python. Va mucho más allá de un bloc de notas: incluye resaltado de sintaxis para 15+ lenguajes, explorador de archivos, terminal integrada, integración con Git, minimap, paleta de comandos y un tema Catppuccin Mocha aplicado hasta el último widget.

---

## Capturas

> _()_

---

## Características

### Editor
- **Resaltado de sintaxis** para 15+ lenguajes, autodetectado por extensión de archivo
- **Code folding** con estilo BoxedTree para colapsar bloques
- **Bracket matching** — resalta paréntesis, llaves y corchetes coincidentes; marca en rojo los no cerrados
- **Guía de columna** en 100 caracteres
- **Indentación automática** con guías visuales, tabs de 4 espacios
- **Zoom** in / out / reset
- **Word wrap** toggle
- **Duplicar línea**, mover línea arriba/abajo, comentar/descomentar
- **Fuente con fallback**: JetBrains Mono → Cascadia Code → Fira Code → Consolas

### Interfaz
- **Pestañas múltiples** con indicador de cambios no guardados (`●`)
- **Confirmación al cerrar** pestañas con cambios pendientes
- **Explorador de archivos** lateral (sidebar) con árbol de directorios
- **Minimap** — vista escalada del archivo activo en el lateral derecho
- **Panel Find & Replace** con soporte de regex, case sensitive y whole-word
- **Terminal integrada** con `QProcess` — ejecuta comandos sin salir del editor
- **Paleta de comandos** (`Ctrl+Shift+P`) con búsqueda fuzzy sobre todas las acciones

### Git
- **Barra de estado** con rama activa y estado dirty/clean (`✦` / `✓`)
- Diálogos integrados para `git status`, `git diff` y `git log --graph`

### Guardado
- **Save All** — guarda todos los archivos abiertos de una vez
- **Autosave** automático cada 30 segundos para archivos con ruta asignada

### Barra de estado
Muestra en tiempo real: posición del cursor (Ln/Col), conteo de palabras, lenguaje del archivo activo y estado de Git.

---

## Lenguajes soportados

| Lenguaje | Extensiones |
|---|---|
| Python | `.py` |
| JavaScript / TypeScript | `.js` `.ts` `.jsx` `.tsx` `.mjs` |
| HTML | `.html` `.htm` |
| CSS | `.css` |
| C / C++ | `.c` `.cpp` `.h` `.hpp` |
| SQL | `.sql` |
| Bash | `.sh` `.bash` |
| XML / SVG | `.xml` `.svg` |
| JSON | `.json` _(si el build lo incluye)_ |
| Markdown | `.md` _(si el build lo incluye)_ |
| Ruby | `.rb` _(si el build lo incluye)_ |
| Perl | `.pl` _(si el build lo incluye)_ |

Los lexers opcionales se cargan dinámicamente — si tu build de QScintilla no los incluye, el editor simplemente los omite sin errores.

---

## Instalación

### Requisitos

- Python 3.10 o superior
- PyQt6
- QScintilla (bindings para PyQt6)

### Instalación de dependencias

```bash
pip install PyQt6 QScintilla
```

> En algunos sistemas puede ser necesario instalar también las herramientas de desarrollo de Qt. Si `QScintilla` no se instala correctamente, consulta la [documentación oficial de Riverbank Computing](https://www.riverbankcomputing.com/software/qscintilla/).

### Ejecutar

```bash
git clone https://github.com/davidtenerife04/notepadpro.git
cd notepadx-pro
Doble click al archivo .exe 
```

---

## Atajos de teclado

| Acción | Atajo |
|---|---|
| Nuevo archivo | `Ctrl+N` |
| Abrir archivo | `Ctrl+O` |
| Guardar | `Ctrl+S` |
| Guardar como | `Ctrl+Shift+S` |
| Guardar todo | `Ctrl+Alt+S` |
| Buscar y reemplazar | `Ctrl+H` |
| Paleta de comandos | `Ctrl+Shift+P` |
| Terminal | `Ctrl+` ` |
| Zoom in | `Ctrl++` |
| Zoom out | `Ctrl+-` |
| Duplicar línea | `Ctrl+D` |
| Comentar/descomentar | `Ctrl+/` |
| Mover línea arriba | `Alt+↑` |
| Mover línea abajo | `Alt+↓` |

---

## Estructura del proyecto

```
notepadx-pro/
└── notepad_pro.py
    │
    ├── LEXER_MAP          Mapa extensión → lexer de QScintilla
    ├── C (Catppuccin)     Paleta de colores Catppuccin Mocha
    ├── apply_dark_theme() Aplica la paleta a QApplication con Fusion style
    ├── Editor             Widget principal (QsciScintilla) con toda la config
    ├── MiniMap            Vista escalada del archivo activo
    ├── FindReplacePanel   Panel de búsqueda con regex
    ├── Terminal           Terminal integrada con QProcess
    ├── CommandPalette     Paleta de comandos con búsqueda en tiempo real
    └── NotepadXPro        Ventana principal — gestión de tabs, Git, menús
```

---

## Tema: Catppuccin Mocha

Toda la interfaz usa la paleta [Catppuccin Mocha](https://github.com/catppuccin/catppuccin), aplicada tanto a los widgets de Qt (via `QPalette` y Fusion style) como al editor Scintilla internamente — fondo, márgenes, cursor, selección, bracket matching, guías de indentación y colores de fold.

---

## Posibles mejoras

- [ ] Autocompletado (usando la API de completions de Scintilla)
- [ ] LSP client básico (pylsp, typescript-language-server...)
- [ ] Sesiones — restaurar pestañas al reabrir
- [ ] Snippets configurables
- [ ] Temas adicionales (Nord, One Dark, Tokyo Night)
- [ ] Soporte para abrir carpetas como proyecto

---

## Licencia

MIT — libre para usar, modificar y distribuir.

---

*Un Notepad que se tomó las cosas muy en serio.*
