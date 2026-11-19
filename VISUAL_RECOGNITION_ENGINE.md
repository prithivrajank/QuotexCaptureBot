# Visual recognition engine

This module is a first-pass image-processing implementation, not a broker feed. It segments common green/red candle colours, detects connected body components, estimates wick extents, and maps vertical pixels to prices using two explicit axis calibration anchors. Candle timestamps can now be estimated from horizontal candle positions using a separate two-point x-axis time calibration.

## Calibration required

The capture config must include both price and time calibration:
```json
{
  "region": {"left": 0, "top": 0, "width": 900, "height": 600},
  "calibration": {
    "y_top": 80,
    "price_top": 1.10500,
    "y_bottom": 520,
    "price_bottom": 1.09500
  },
  "time_calibration": {
    "x_left": 100,
    "timestamp_left": 1795000000,
    "x_right": 700,
    "timestamp_right": 1795003600
  }
}
```
All values above are placeholders. Replace them with the actual capture-region pixel coordinates and Unix timestamps for two candle-center positions on the visible time axis. The right anchor timestamp must be later than the left anchor. The local agent maps each detected candle's x-center to the nearest timeframe slot. For a one-minute chart, anchors should refer to candle centers and be separated by a known time interval.

Keep chart scale, zoom, capture region, and timeframe fixed after calibration. Recalibrate after resizing, zooming, changing theme, moving the chart, changing timeframe, or changing visible candle spacing. Do not use the timestamp labels as if the program OCR-read them: anchors are manually supplied.

## Run

```cmd
set BOT_API_URL=https://YOUR-RENDER-SERVICE.onrender.com
set INGEST_TOKEN=YOUR_LONG_RANDOM_SECRET
python -m app.local_agent --symbol EURUSD_OTC --timeframe 60
```

## Timestamp and history behavior

- Every detected candle is mapped from its horizontal pixel center to a candle timestamp.
- Candles earlier than the current local timeframe slot are sent as closed; the current slot is sent as forming.
- Future projected positions and very old positions are skipped.
- The agent can now submit multiple visible candles, not only the rightmost candle.
- Repeated unchanged payloads are suppressed locally. The API's closed-candle upsert rule prevents a closed candle from being reopened.
- The chart's horizontal spacing must represent a consistent time scale. If the platform inserts gaps, hides candles, or uses a non-linear/irregular x-axis, this linear mapping will be wrong.

## Important limits

- This is manual two-anchor calibration, not automatic OCR of chart-axis labels.
- Colour ranges depend on chart theme; defaults are green and red. Adjust the palette for other colours.
- Body connected components can merge with wicks or overlays. Confidence is heuristic, not a statistical probability.
- Pixel-to-price and pixel-to-time estimates must be compared against visible Demo candles before relying on outputs.
- If chart layout, scale, theme, timeframe, or zoom changes, stop and recalibrate.
- Signals remain experimental; no order execution is implemented.
