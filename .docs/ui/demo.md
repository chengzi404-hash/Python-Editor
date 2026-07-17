# `ui.demo`

**Source**: [`ui/demo.py`](../../ui/demo.py) — 367 lines.

Component gallery that exercises every public widget in
`ui.widgets`. Used as both a visual smoke test and a copy-paste
reference for new apps.

## Running

```bash
python -m ui.demo           # entry point
```

Equivalent from Python:

```python
from ui.demo import main
main()
```

The gallery opens a window titled `Uui Component Gallery`, builds a
left-side menu (`File / Edit / View / Help`), a header with a theme
picker, and a scrollable body containing:

1. **Buttons** — one of every `variant` (`default`, `primary`,
   `success`, `danger`, `warning`, `ghost`) plus a disabled state.
2. **Text Input** — `UEntry` (name / email / password / search).
3. **Selection** — `UCheckButton`, `URadioButton`, `UComboBox`.
4. **Progress & Slider** — `UProgressBar` + `USlider` linked together.
5. **Live Editor** — `UText` with wrap + sample text.

It also enables `theme.follow_system(...)` so the demo tracks the OS
appearance when the user toggles the "Follow system" checkbox.

## Public surface

```python
from ui.demo import build_demo, main

build_demo(window)   # Build the full demo inside the given Window.
main()               # Create the demo Window, call build_demo, run mainloop.
```

`build_demo(window)` is the interesting entry point for embedding the
gallery in another application — it does not run the mainloop and does
not create the `Window` itself.

## Implementation notes

- The scrollable body is hand-rolled from a `tk.Canvas` + `tk.Frame`
  + `UScrollBar` because `ui.widgets` does not (yet) ship a
  `UScrollableFrame`.
- The theme picker uses `theme.on_change(callback)` to keep the
  `UComboBox` in sync with `theme.set_theme(...)`.
- The "Follow system" checkbox toggles `theme.follow_system(...)` /
  `theme.stop_following()` at runtime; the demo re-applies the theme
  recursively via `theme.set_theme(target, refresh_root=window)`.