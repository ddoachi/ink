# Toolbar Icons

This directory contains SVG icon resources for the Ink schematic viewer toolbar.
These icons serve as fallbacks when system icon themes are not available.

## Icon Set Information

**Style**: Tabler Icons style (clean, minimal, monochrome)
**Format**: SVG with `currentColor` for theme adaptation
**Size**: 24x24 viewport, scalable vector
**License**: MIT License (see below)

## Icons Included

| File Name | Freedesktop Name | Purpose | Description |
|-----------|------------------|---------|-------------|
| `document-open.svg` | document-open | Open file | Folder icon with arrow |
| `edit-undo.svg` | edit-undo | Undo action | Arrow pointing back |
| `edit-redo.svg` | edit-redo | Redo action | Arrow pointing forward |
| `edit-find.svg` | edit-find | Search/find | Magnifying glass |
| `zoom-in.svg` | zoom-in | Zoom in | Magnifying glass with + |
| `zoom-out.svg` | zoom-out | Zoom out | Magnifying glass with - |
| `zoom-fit-best.svg` | zoom-fit-best | Fit view | Corner arrows (maximize) |

## Design Principles

1. **Monochrome with `currentColor`**: Icons use `stroke="currentColor"` to
   automatically adapt to light/dark themes.

2. **Consistent Style**: All icons share the same stroke width (2px),
   line caps (round), and line joins (round).

3. **Scalable Vector**: SVG format ensures crisp rendering at any size,
   especially important for high-DPI displays.

4. **Freedesktop Naming**: File names follow freedesktop.org icon naming
   conventions for consistency with system themes.

## License

These icons are based on the Tabler Icons style and are licensed under the MIT License.

```
MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Usage

Icons are compiled into the application via the Qt Resource System:

```bash
# Compile resources (run from project root)
pyside6-rcc resources/resources.qrc -o src/ink/presentation/resources_rc.py
```

Then use `IconProvider` to load icons with theme fallback:

```python
from ink.presentation.utils.icon_provider import IconProvider

# Get icon (tries theme first, falls back to bundled SVG)
icon = IconProvider.get_icon("zoom-in")
action.setIcon(icon)
```

## Adding New Icons

1. Create SVG file with 24x24 viewport
2. Use `currentColor` for stroke and fill
3. Follow freedesktop.org naming conventions
4. Add file to `resources.qrc`
5. Add mapping in `IconProvider.ICON_MAP`
6. Recompile resources

## See Also

- [Tabler Icons](https://tabler-icons.io/) - Icon design inspiration
- [Freedesktop Icon Naming](https://specifications.freedesktop.org/icon-naming-spec/latest/) - Naming conventions
- [Qt Resource System](https://doc.qt.io/qt-6/resources.html) - Resource compilation docs
