# Visual recognition engine

This module is a first-pass image-processing implementation, not a broker feed. It segments common green/red candle colours, detects connected body components, estimates wick extents, and maps vertical pixels to prices using two explicit axis calibration anchors.

## Calibration required
The capture config must include:
```json
{
  "region": {"left": 0, "top": 0, "width": 900, "height": 600},
  "calibration": {
    "y_top": 80,
    "price_top": 1.10500,
    "y_bottom": 520,
    "price_bottom": 1.09500
  }
}
```
The example prices and pixels are placeholders only. Replace them with the two actual visible price-axis anchors from the user's chart. Keep chart scale, zoom, and region fixed after calibration. Recalibrate after resizing, zooming, changing theme, or moving the chart.

## Run
```cmd
set BOT_API_URL=https://YOUR-RENDER-SERVICE.onrender.com
set INGEST_TOKEN=YOUR_LONG_RANDOM_SECRET
python -m app.local_agent --symbol EURUSD_OTC --timeframe 60
```

## Important limits
- Colour ranges depend on chart theme; defaults are green and red. Adjust the palette for other colours.
- The detector does not yet infer candle timestamps from chart x-axis labels. The local agent currently assigns the current timeframe slot, so historical candle positions must not be treated as time-accurate.
- Body connected components can merge with wicks or overlays. Confidence is heuristic, not a statistical probability.
- The first implementation must be calibrated and compared against visible Demo candle OHLC before relying on any output. If chart layout, scale, or theme changes, stop and recalibrate.
- Signals remain experimental; no order execution is implemented.
