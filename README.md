# macshot — macOS-style window screenshots for Windows

Capture windows and screen regions with a macOS-inspired style:

- **Original window size** — pixel-perfect, no resizing.
- **Rounded corners** — anti-aliased, like a real macOS window.
- **Soft drop shadow** — a gentle downward shadow.
- **Transparent background** — saved as PNG with a real alpha channel, ready to
  drop onto slides, docs, or designs.

It captures the *on-screen pixels* via the desktop device context, so it works
for hardware-accelerated content too — **games, browsers and video included**.

![example](tests/demo_effect.png)

---

## Build the Windows app

```powershell
python -m pip install -r requirements.txt
.\build_exe.ps1
```

Requires Python 3.9+ on Windows 10/11. The build writes the desktop app to
`dist\Macshot.exe`.

## Use

Double-click **`dist\Macshot.exe`**. Macshot starts as a standard Windows tray app
without opening a console window and shows the Home window immediately.

- Press **Ctrl + Shift + S** to capture a window.
- Use **Settings** to switch between automatic language detection, English and
  Simplified Chinese.
- Or use the tray menu directly:
  - **Capture Window**: click a highlighted window in the overlay.
  - **Capture Full Screen**: capture the full virtual desktop.
  - **Capture Region**: drag a rectangular region.
  - **Capture Circle**: drag a circle and keep only the pixels inside it.
  - **Free-form Screenshot**: draw a freehand shape and keep only the pixels
    inside it.
- In any overlay, press **Esc** or right-click to cancel.
- Results are saved to `%USERPROFILE%\Pictures\Macshot` and copied to the
  clipboard.
- After a screenshot, click the Macshot saved notification to open the output
  folder.
- Use **Settings** from the tray or home window to change output, clipboard,
  hotkey and style options. Settings are saved under your Windows app data folder.
- Use the tray menu to open the output folder or exit the app.

To start Macshot automatically at login, put a shortcut to `dist\Macshot.exe` in
your Startup folder (`Win+R` -> `shell:startup`).

## Developer CLI

From a terminal:

```powershell
# Run the tray app
python -m macshot

# Pick a window interactively once — click it, Esc to cancel
python -m macshot --pick

# Capture the current foreground window after a 3-second countdown
python -m macshot --foreground -d 3

# Capture the first window whose title contains some text
python -m macshot --title "崩坏"

# List every capturable window
python -m macshot --list
```

## Output options

| Flag | Meaning |
|------|---------|
| `-o, --out DIR` | output folder (default `~/Pictures/Macshot`) |
| `--open` | open the output folder afterwards |
| `--no-clipboard` | don't copy the result to the clipboard |

## Tuning the look

All values are in pixels at 100% scaling and are scaled automatically for high-DPI
monitors.

| Flag | Default | Meaning |
|------|---------|---------|
| `--radius` | 11 | corner radius |
| `--padding` | 90 | transparent margin around the window |
| `--no-shadow` | — | turn the shadow off |
| `--shadow-opacity` | 0.45 | shadow strength (0–1) |
| `--shadow-blur` | 34 | shadow softness |
| `--shadow-offset` | 22 | how far the shadow falls downward |

Example — a tighter, softer shadow:

```powershell
python -m macshot --shadow-blur 45 --shadow-opacity 0.35 --padding 110
```

## How it works

1. **Find the window** — by click, foreground, or title match.
2. **Measure it** — `DwmGetWindowAttribute(EXTENDED_FRAME_BOUNDS)` gives the true
   visible rectangle (no invisible resize border), in physical pixels.
3. **Grab the pixels** — `BitBlt` from the screen DC, so GPU-rendered content is
   captured exactly as shown.
4. **Apply the Mac look** — round the corners with an anti-aliased mask, lay down a
   blurred drop shadow on a transparent canvas, and composite the window on top
   (`macshot/effect.py`).
5. **Deliver** — save a transparent PNG and copy it to the clipboard as `CF_DIBV5`
   (alpha-preserving) plus a raw `PNG` clipboard format.

## Project layout

```
macshot/         app source
tests/           lightweight effect checks
build_exe.ps1    builds dist/Macshot.exe
requirements.txt dependencies
```

## Notes & limits

- The corners of a captured window show whatever the desktop placed behind them;
  the rounded mask trims that away (plus a 1px edge `trim`) so no desktop seam
  leaks in.
- Capturing brings the target window to the front first (skip with `--no-raise`).
- Full screen and region modes also use physical screen pixels. Free and circle
  region captures disable the window-only 1px edge trim so the selected source
  pixels are preserved exactly.
- For multi-monitor mixed-DPI setups, window capture uses each window's own DPI;
  region capture uses the selected region's center monitor for styling scale. The
  picker overlay highlight may be a pixel or two off on a secondary monitor.
