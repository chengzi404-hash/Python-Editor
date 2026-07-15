# `modules.Uui.tool`

**Source**:
- [`__init__.py`](../../modules/Uui/tool/__init__.py) — empty
- [`designer.py`](../../modules/Uui/tool/designer.py) — 1844 lines

The Visual Widget Designer: a Qt Creator-inspired WYSIWYG editor for
laying out Tk windows built from `modules.Uui.widgets`.

```python
from modules.Uui.tool.designer import DesignerApp, main
DesignerApp().mainloop()       # opens the designer window
```

## Module-level constants

| Name | Value |
| --- | --- |
| `DESIGNER_VERSION` | `'2.0'` |
| `WIDGET_TYPES` | `['UFrame', 'ULabel', 'UButton', 'UEntry', 'UText', 'UCheckButton', 'URadioButton', 'UComboBox', 'UProgressBar', 'USlider']` |
| `WIDGET_CLASSES` | Mapping `name -> class` for runtime instantiation. |
| `DEFAULT_PROPS` | Default per-widget property values used by the designer. |
| `DEFAULT_SIZE` | Default width / height per widget type. |
| `VARIANT_OPTIONS` | Allowed `variant` values per widget type. |
| `NUMERIC_PROPS` | `{'x', 'y', 'width', 'height', 'maximum', 'value', 'from_', 'to'}` |
| `BOOL_PROPS` | `{'show_value'}` |
| `WIDGET_GROUPS` | Logical grouping shown in the sidebar. |
| `WIDGET_ICON` | Mapping `widget_type -> unicode icon character`. |

## Classes

### Internal helpers (not public API)

- `_FlatButton(tk.Frame)` — minimal flat button used by the designer UI.
- `_PanelSection(tk.Frame)` — labelled panel wrapper.
- `_SidebarTabBar(tk.Frame)` — sidebar tab strip.

### `DesignerApp(Window)` — public

`Window` subclass providing the full designer UI: widget palette,
canvas, properties inspector, and project save/load. Constructs a
default blank project.

### `main(project_file=None)` — public entry point

```python
def main(project_file: Optional[str] = None) -> None
```

Launches the designer. Pass `project_file` to open an existing
`.uui.xml` / `.uui` layout at startup. Typically invoked from
`modules/Uui/cli.py`.

## File format

Designer projects are XML (root element `<uui version="2.0">`)
containing one `<widget>` per node with attributes for type, parent,
geometry and properties. `DESIGNER_VERSION` is bumped when the schema
breaks compatibility.

## CLI integration

The designer is exposed through `python -m Uui` (see
[`modules/Uui/cli.py`](../../modules/Uui/cli.py)). Available subcommands:

- `python -m Uui designer` — open the designer.
- `python -m Uui designer path/to/project.uui` — open with a project.
- `python -m Uui new <name>` — scaffold a project skeleton.