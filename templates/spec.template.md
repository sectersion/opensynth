# opensynth design spec template
# Copy to <design_dir>/spec.md and fill in. The RTL agent reads this.

# <design name> — <one-line summary>

## Overview
What the design does, in 2-3 sentences. State the intent, not the implementation.

## Interface
| Port | Dir | Width | Description |
|---|---|---|---|
| clk | in | 1 | system clock |
| rst_n | in | 1 | synchronous, active-low reset |

## Behavior
Numbered, testable statements. Each one should map to at least one testbench check.
1. On reset, all outputs go to <state>.
2. When <enable> is high, <behavior>.
3. When <enable> is low, outputs hold their value.

## Parameters
| Name | Default | Meaning |
|---|---|---|
| WIDTH | 8 | counter width |

## Timing
- Target clock period: 10 ns (100 MHz) — copy to design.yaml `timing.clock_period_ns`.

## Out of scope
Explicitly list what this design does NOT do (avoids agent over-engineering).
