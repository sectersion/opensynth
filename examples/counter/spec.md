# counter — 8-bit free-running up counter

## Overview
A parameterizable up-counter. Counts at one increment per clock when enabled, holds when disabled, and returns to zero on reset. Used as the opensynth reference design: small enough to run the full flow in minutes, complete enough to exercise reset, enable, hold, and wraparound.

## Interface
| Port | Dir | Width | Description |
|---|---|---|---|
| clk | in | 1 | system clock, rising-edge |
| rst_n | in | 1 | synchronous, active-low reset to 0 |
| enable | in | 1 | when high, counter increments each cycle |
| count | out | WIDTH | current count value |

## Behavior
1. While `rst_n` is low, `count` is 0 on the next rising clock edge.
2. While `enable` is high and `rst_n` is high, `count` increments by 1 each rising clock edge, wrapping from `2^WIDTH-1` back to 0.
3. While `enable` is low and `rst_n` is high, `count` holds its value.
4. Reset is synchronous: no effect until a rising clock edge.

## Parameters
| Name | Default | Meaning |
|---|---|---|
| WIDTH | 8 | counter width in bits |

## Timing
- Target clock period: 10 ns (100 MHz).

## Out of scope
- No down-counting, no load input, no compare/terminal-count output.
- No asynchronous reset.
