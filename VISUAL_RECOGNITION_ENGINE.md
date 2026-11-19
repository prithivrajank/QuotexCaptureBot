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


## Profile validation before capture

The local capture agent and multi-profile launcher validate the profile before opening screen capture. They reject missing calibration, non-finite values, non-positive prices, anchors outside the crop, invalid time order, empty symbols, and invalid timeframe values. All calibration pixel coordinates are relative to the cropped image, not absolute desktop coordinates. The `region.left/top` values are absolute desktop coordinates; `calibration.y_*` and `time_calibration.x_*` are crop-relative. This prevents a common coordinate-system mix-up.

Validation only checks that the values are structurally plausible. It cannot prove that the selected price/time labels were read correctly or that candle centers align with real timestamps. Manual Demo comparison is still required. Signal generation remains disabled by default until this review is complete.

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


## Candle detector filtering

The detector now removes long horizontal/vertical structures from the colour masks before connected-component analysis, then estimates the dense candle-body rows separately from thin wick pixels. Candidate confidence is reduced for sparse shapes and components dominated by thin lines. This is a heuristic improvement only: coloured overlays, unusually thin candles, shadows, annotations and chart themes can still cause false detections or missed candles. The synthetic detector tests are committed but have not been executed in this workflow. Compare detected candles with the live Demo chart before enabling signal generation.


## Timestamp sequence checks

Detected candidates are mapped to timeframe slots and sorted by timestamp before ingestion. If multiple candidates map to the same slot, only the highest-confidence candidate is kept and a duplicate warning is logged. Missing time slots between visible detections are reported as gaps; the agent does not invent or interpolate candles. These diagnostics help reveal poor crop selection, detection misses or inaccurate x-axis calibration. A gap warning is not proof of a market-data outage because some chart layouts may hide candles or have irregular spacing. Review the visible Demo chart and recalibrate when warnings persist.

## Reconstructed-candle validation

Before a pixel candidate is converted to OHLC, the agent checks that the candle colour is recognized, body and wick bounds are ordered, the body width and height are within conservative limits, and confidence is within 0..1. Reconstructed prices must be finite and positive, and OHLC high/low must contain the open and close. Invalid candidates are skipped and logged as `candle_candidate_rejected`; they are not sent to history. These checks reject malformed geometry but cannot prove that a visually detected shape is a real broker candle. Compare accepted estimates with the visible Demo chart.

Older capture agents that omit timestamp-alignment diagnostics retain the backward-compatible `ALIGNED` default. The current agent explicitly reports `NO_CANDLES` when no candidates are detected.

## Missing and merged-candle diagnostics

Sequence diagnostics now report the exact number of missing timeframe slots, the number of separate gaps, and the largest gap. To keep requests bounded, only up to 1000 missing timestamps are included in the detailed list; the aggregate count remains exact. The dashboard displays the aggregate missing-slot count and largest gap rather than treating the capped list length as the total. Duplicate candidates mapped to the same timestamp are still reduced to the highest-confidence candidate and counted. No missing or suspected merged candle is synthesized. These metrics identify suspicious visual sequences, but cannot distinguish a detector miss from hidden chart candles, a crop error, or irregular chart spacing without manual chart review.

## Merged-candle detection and score gates

Oversized connected colour regions are now examined using their vertical pixel-density projection. A wide region is split only when a sufficiently deep low-density valley separates its sides; an unsplittable wide blob is rejected instead of being guessed into several candles. This can recover some candles joined by thin wicks, but cannot reliably separate bodies that touch with no visible valley. The detector's confidence field is a heuristic shape-quality score, not a probability. The score formula and the API acceptance gate are aligned (0.75); the signal strategy applies stricter recent-candle quality gates (0.80 latest, 0.72 recent history). No score proves that a detected candle is correct.

Reconstructed candles must also have positive finite prices and a timestamp aligned to their configured timeframe. The API model independently enforces positive OHLC values and aligned candle slots. A GitHub Actions workflow now runs the Python test suite on pushes to the working branch and on pull requests to main. Workflow success must be checked on GitHub; adding the workflow does not mean tests have already passed.
