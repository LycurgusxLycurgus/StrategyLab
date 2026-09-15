import assert from "node:assert/strict";
import { test } from "node:test";
import { PineTS } from "pinets";

const candles = [
  { time: 1704067200000, open: 100, high: 102, low: 99, close: 101, volume: 10 },
  { time: 1704067260000, open: 101, high: 103, low: 100, close: 102, volume: 11 },
  { time: 1704067320000, open: 102, high: 104, low: 101, close: 103, volume: 12 },
  { time: 1704067380000, open: 103, high: 105, low: 102, close: 104, volume: 13 },
  { time: 1704067440000, open: 104, high: 106, low: 103, close: 105, volume: 14 },
].map((bar) => ({ ...bar, openTime: bar.time }));

test("PineTS executes caller-supplied OHLCV without a provider", async () => {
  const runtime = new PineTS(candles);
  const context = await runtime.run(`
//@version=6
indicator("capability")
plot(ta.sma(close, 2), "p2p__feature__sma")
`);
  assert.ok(context.plots);
  assert.ok(Object.keys(context.plots).length > 0);
});

test("PineTS strategy namespace returns strategy state", async () => {
  const runtime = new PineTS(candles);
  const context = await runtime.run(`
//@version=6
strategy("capability", initial_capital=10000)
if bar_index == 1
    strategy.entry("L", strategy.long, qty=1)
if bar_index == 3
    strategy.close("L")
plot(strategy.position_size, "p2p__state__position")
`);
  assert.ok(context.strategy);
  assert.ok(Array.isArray(context.strategy.closedtrades));
});
