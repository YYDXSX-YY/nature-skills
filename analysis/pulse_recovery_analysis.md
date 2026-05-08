# Pulse recovery figure analysis

## Data inspection

The workbook `data/133.xlsx` contains three sheets:

| Sheet | Rows inspected | Header / role |
|---|---:|---|
| `前` | 347 | Crack-object table with columns `ID`, `Area`, `Length`, `Width`, `Direction`, `End A`, `End B`, followed by summary text in additional populated cells. |
| `后` | 117 | Crack-object table with columns `ID`, `Area`, `Length`, `Width`, `Direction`, `End A`, `End B`, followed by summary text in additional populated cells. |
| `导出计数` | 3338 | Exported width/count table. Row 1 labels the conditions: `流速1 注3停3 驱前`, `流速1 注3停3 驱后`, `压井液驱`, `后续水驱`. Row 2 defines width columns plus binned summaries: `区间`, `范围`, `统计1`, `统计2`, `统计3`, `统计4`, `饱和油`, `水驱油`, `注压井液`, `后续水驱`. |

The `导出计数` sheet is a typical two-dimensional binned table: rows are width intervals and columns are condition-specific counts or percentages. Therefore, the minimal figure uses a two-series line chart to compare the percentage distribution before and after the pulse-recovery condition.

## Figure generated

The script `scripts/plot_pulse_recovery.py` reads `data/133.xlsx` without modifying it, extracts the binned width percentages from `导出计数`, and writes the editable SVG figure to `figures/pulse_recovery.svg`.

## Main pattern

- The total binned observations decrease from 345 before recovery to 115 after recovery.
- Before recovery, the distribution peaks at the `2-3` width interval, where 159 observations account for 46.09% of the total.
- After recovery, the peak shifts to the narrower `1-2` interval, where 42 observations account for 36.52% of the total; the `2-3` interval remains high at 33.04%.
- Wider intervals above `3-4` generally contribute smaller shares in both states, indicating that most measured widths are concentrated in the low-width bins.
- The line chart therefore suggests a post-recovery redistribution toward narrower width classes, alongside a lower total number of counted objects.
