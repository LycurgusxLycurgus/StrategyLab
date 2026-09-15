import fs from "node:fs/promises";
import process from "node:process";
import { PineTS } from "pinets";

function toPlain(value, depth = 0, seen = new WeakSet()) {
  if (value === null || value === undefined) return value ?? null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "bigint") return Number(value);
  if (typeof value === "function") return undefined;
  if (depth > 12) return "[depth-limit]";
  if (typeof value === "object") {
    if (seen.has(value)) return "[circular]";
    seen.add(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => toPlain(item, depth + 1, seen));
  }
  if (value instanceof Map) {
    return Object.fromEntries(
      [...value.entries()].map(([key, item]) => [
        String(key),
        toPlain(item, depth + 1, seen),
      ]),
    );
  }
  if (typeof value === "object") {
    const output = {};
    for (const [key, item] of Object.entries(value)) {
      if (key.startsWith("_") || key === "context") continue;
      const plain = toPlain(item, depth + 1, seen);
      if (plain !== undefined) output[key] = plain;
    }
    return output;
  }
  return String(value);
}

function normalizeCandle(candle) {
  return {
    openTime: Number(candle.time),
    closeTime: Number(candle.closeTime ?? candle.time),
    open: Number(candle.open),
    high: Number(candle.high),
    low: Number(candle.low),
    close: Number(candle.close),
    volume: Number(candle.volume ?? 0),
  };
}

async function main() {
  if (process.argv.length !== 4) {
    throw new Error("usage: node worker.mjs REQUEST_JSON RESULT_JSON");
  }
  const [, , requestPath, resultPath] = process.argv;
  const request = JSON.parse(await fs.readFile(requestPath, "utf8"));
  const candles = request.candles.map(normalizeCandle);
  const runtime = new PineTS(
    candles,
    request.symbol ?? "CUSTOM",
    request.timeframe ?? "1",
  );
  const context = await runtime.run(request.source);
  const result = {
    schema_version: "1.0",
    runtime: {
      name: "PineTS",
      version: "0.9.29",
      official_tradingview: false,
    },
    indicator: toPlain(context.indicator),
    plots: toPlain(context.plots),
    strategy: toPlain(context.strategy),
    alerts: toPlain(context.alerts),
    warnings: [
      "PineTS execution is local supported-subset evidence, not official TradingView verification.",
    ],
  };
  await fs.writeFile(resultPath, JSON.stringify(result));
}

main().catch(async (error) => {
  const failure = {
    schema_version: "1.0",
    error: {
      name: error?.name ?? "Error",
      message: String(error?.message ?? error),
      stack: String(error?.stack ?? ""),
    },
  };
  if (process.argv[3]) {
    try {
      await fs.writeFile(process.argv[3], JSON.stringify(failure));
    } catch {
      // The caller still receives the nonzero exit code and stderr.
    }
  }
  process.stderr.write(`${failure.error.name}: ${failure.error.message}\n`);
  process.exitCode = 1;
});
