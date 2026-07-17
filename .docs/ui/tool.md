# `ui.tool`

**Source**: [`ui/tool/`](../../ui/tool/) — single-file package containing
just the visual widget designer.

```text
ui/tool/
├── __init__.py        # empty re-export module
└── designer.py        # visual designer + XML scene loader
```

The designer is launched either from inside the editor (via the View
menu) or from the CLI (`python -m ui.cli designer [file.xml]`).

## Visual widget designer (`ui.tool.designer`)

A Canvas-based GUI for laying out `ui.widgets` widgets. The user drags
widgets onto a scene, arranges them, edits their properties, and saves
the result as an XML file. The XML is consumed by the editor's
"Load scene" feature (and by `ui.cli` projects) to reproduce the layout
without manual Tk code.

```python
from ui.tool.designer import main
main()                              # launch with a new empty scene
main("/path/to/scene.xml")          # open an existing scene
```

### Top-level entry point

| Function | Description |
| --- | --- |
| `main(project_file=None)` | Open the designer window. When `project_file` is supplied, load that XML scene; otherwise start blank. |

The internal implementation is private and consists of:

- A scene model holding widgets, their properties, and the parent/child
  graph.
- A `tk.Canvas`-backed editor surface with drag / snap / resize.
- A property panel (`ttk.Treeview`-style) for editing each widget's
  constructor kwargs.
- An XML serializer that emits files consumable by the editor's scene
  loader.

See the source for the public surface; everything except `main` is
considered implementation detail.

## Public surface

`ui.tool.__init__` is empty by design. Always import from
`ui.tool.designer` explicitly.