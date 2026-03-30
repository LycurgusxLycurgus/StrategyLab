

# Strategy Codification Canon

## White-Box, Black-Box, and Hybrid Approaches to Transforming Trading Ideas into Executable Code

---

## Table of Contents

1. [Why This Document Exists](#1-why-this-document-exists)
2. [The Codification Spectrum: Definitions](#2-the-codification-spectrum-definitions)
3. [White-Box Strategies: Complete Reference](#3-white-box-strategies-complete-reference)
4. [Black-Box Strategies: Complete Reference](#4-black-box-strategies-complete-reference)
5. [Hybrid Strategies: Complete Reference](#5-hybrid-strategies-complete-reference)
6. [The Universal Transformation Process](#6-the-universal-transformation-process)
7. [Codification Patterns Catalog](#7-codification-patterns-catalog)
8. [Worked Examples: Manual Strategy to Code](#8-worked-examples-manual-strategy-to-code)
9. [Component and Building Block Reference](#9-component-and-building-block-reference)
10. [Decision Framework: Choosing Your Approach](#10-decision-framework-choosing-your-approach)
11. [Failure Modes and How to Avoid Them](#11-failure-modes-and-how-to-avoid-them)
12. [Glossary](#12-glossary)

---

## 1. Why This Document Exists

Every trading strategy begins as an idea. That idea might be a discretionary trader's intuition ("I buy when price sweeps a prior low and then reclaims it during the London session"), a macro thesis ("when real yields go negative, gold outperforms"), or a statistical observation ("these two stocks diverge and then revert within 5 days 63% of the time").

The challenge is always the same: **how do you turn that idea into code that a machine can execute consistently, test rigorously, and improve systematically?**

There is no single answer. The way you codify a strategy depends on:

- How well you understand *why* the edge exists
- Whether the edge can be described in explicit rules or must be learned from data
- How much historical data you have
- How fast the strategy must execute
- How much you need to understand the strategy's failures

This document defines **three codification approaches**—White-Box, Black-Box, and Hybrid—with enough precision and detail that you can take any trading idea and know exactly how to transform it into working code using any of the three approaches, or create entirely new strategies from scratch within any of these frameworks.

---

## 2. The Codification Spectrum: Definitions

### 2.1 The Spectrum Is Not Binary

White-box and black-box are not two buckets. They are the endpoints of a continuous spectrum defined by a single axis: **how much of the strategy's decision logic is explicitly written by a human versus learned from data by a model.**

```
FULL WHITE-BOX                                                    FULL BLACK-BOX
|────────────────────────────────────────────────────────────────────────|
Every rule is          Some rules explicit,       All decisions made
written by a human.    some learned from data.    by a trained model.
You can read the       You can read parts         You can see inputs
code and know          but some thresholds        and outputs, but the
exactly why every      or filters come from       internal decision
trade was taken.       statistical fitting.       path is opaque.
                              |
                          HYBRID ZONE
```

### 2.2 White-Box: Formal Definition

A **white-box strategy** is one where every decision the strategy makes—when to enter, when to exit, how much to risk, which instruments to trade, and under what conditions to do nothing—is encoded as **explicit, human-readable rules** that can be inspected, understood, and explained line by line.

**The defining test:** Can a non-technical trader read the strategy's decision logic (or a plain-language translation of it) and predict exactly what the strategy would do on any given bar of data? If yes, it is white-box.

**What "explicit rules" means concretely:**

- Every condition is a logical expression: `if price > moving_average(200)`, `if RSI < 30`, `if spread between asset A and asset B > 2 standard deviations`
- Every threshold is a fixed number or a number derived from a formula you can write down: `stop_loss = entry_price - 2 * ATR(14)`
- Every state transition is a defined path: `if in_state("waiting") and breakout_detected: transition_to("entry_pending")`
- There are no learned weights, no trained parameters, no neural network layers, no fitted coefficients that emerged from an optimization process the human cannot fully trace

**Origins (The Dalio / Bridgewater Paradigm):**

Ray Dalio's Bridgewater Associates is the archetype. Dalio's belief: the economy is a machine with logical cause-and-effect relationships. If you understand those relationships, you can write them down. If you can write them down, you can code them. If you can code them, you can test them against 100+ years of data. If a model says "buy gold," Dalio demands to know *exactly why*—because real yields are negative, because central banks are printing money, because debt-to-GDP ratios have crossed a threshold. A model that says "buy gold because my neural network says so" is unacceptable in this paradigm because it cannot anticipate unprecedented events it has never seen in training data.

### 2.3 Black-Box: Formal Definition

A **black-box strategy** is one where the core trading decisions are made by a **trained model** whose internal decision logic is not explicitly written by a human and cannot be fully inspected or explained at the individual-decision level.

**The defining test:** Can you look at a specific trade the strategy took and trace, step by step, through human-readable rules to explain exactly why that trade was taken? If you cannot—if the answer is "the model's output exceeded the threshold" and the model is a neural network with thousands of learned weights—it is black-box.

**What "trained model" means concretely:**

- A neural network (LSTM, Transformer, CNN, etc.) that was trained on historical data and whose weights were learned through backpropagation
- A random forest or gradient-boosted ensemble whose splits were learned from data
- A reinforcement learning agent whose policy was learned through simulated or live interaction with market data
- Any model where the mapping from inputs to outputs passes through learned parameters that a human did not set by hand

**Origins (The Simons / Renaissance Technologies Paradigm):**

Jim Simons' Renaissance Technologies is the archetype. Simons was a mathematician, not an economist. His belief: markets contain statistical patterns that can be found by analyzing data at massive scale. You do not need to know *why* asset B goes up when data point A occurs. You need to know *that it does*, with statistical significance, after accounting for transaction costs, across enough data to trust the pattern. The only metric that matters is risk-adjusted return (Sharpe ratio). If an uninterpretable model produces a higher Sharpe ratio than an interpretable one, the uninterpretable model wins.

### 2.4 Hybrid: Formal Definition

A **hybrid strategy** combines explicit human-written rules with model-learned components. The human provides the structural framework, and statistical or machine-learning methods fill in specific parameters, filters, or decision layers within that framework.

**The defining test:** Can you identify which parts of the strategy are explicit rules you wrote and which parts are outputs of a trained model? If the strategy has both, and you can clearly separate them, it is hybrid.

**What "hybrid" looks like concretely:**

- A white-box entry signal (price crosses above VWAP during London session) combined with a machine-learning filter that scores the probability of follow-through based on recent volatility regime, order flow features, and time-of-day patterns
- An explicit state machine (waiting → setup detected → entry → managing → exit) where the state transitions are human-defined but the parameters (which moving average length? which ATR multiplier for the stop?) are optimized by a statistical process against historical data
- A rule-based portfolio allocation framework (risk parity across asset classes) where the regime classification (are we in "rising growth / rising inflation" or "falling growth / falling inflation"?) is performed by a Hidden Markov Model

---

## 3. White-Box Strategies: Complete Reference

### 3.1 The Anatomy of a White-Box Strategy

Every white-box strategy, regardless of the market, timeframe, or specific trading idea, is built from the same structural components. Understanding these components is what allows you to take *any* manual strategy and codify it.

#### Component 1: Market Context Filter

**What it does:** Determines whether the strategy should even be active right now. This is the outermost gate.

**How a discretionary trader thinks about it:** "I only trade during London and New York sessions." "I don't trade on NFP days." "I only look for longs when the weekly trend is up."

**How it becomes code:**

```
# These are explicit, inspectable conditions
def is_context_valid(current_bar, daily_data, calendar):
    # Session filter
    if current_bar.time not in LONDON_SESSION and current_bar.time not in NY_SESSION:
        return False

    # News filter
    if calendar.has_high_impact_event(current_bar.date, within_minutes=30):
        return False

    # Higher-timeframe trend filter
    weekly_trend = compute_trend(daily_data, method="structure", lookback=20)
    if weekly_trend == "bearish" and desired_direction == "long":
        return False

    return True
```

**Key property:** Every condition is a readable boolean expression. No learned weights. No model inference. A human wrote every line.

#### Component 2: State Machine

**What it does:** Defines the discrete states the strategy can be in and the allowed transitions between them. This is the backbone of the strategy's logic flow.

**How a discretionary trader thinks about it:** A discretionary trader doesn't usually think in terms of "states" explicitly, but they absolutely operate with them implicitly: "I'm waiting for a setup" → "I see a setup forming" → "The setup triggered, I'm in a trade" → "I'm managing the trade" → "I'm out." Codifying a strategy means making these implicit states explicit.

**Standard state machine for most strategies:**

```
States:
  IDLE          → No position, no setup detected, waiting
  SETUP         → Conditions partially met, watching for trigger
  ENTRY_PENDING → Trigger fired, order placed but not yet filled
  IN_POSITION   → Order filled, trade is live
  MANAGING      → In position, adjusting stops/targets based on price action
  EXIT_PENDING  → Exit signal fired, exit order placed
  COOLDOWN      → Just exited, waiting before looking for new setups

Transitions:
  IDLE → SETUP:           when setup_conditions_met()
  SETUP → IDLE:           when setup_invalidated()
  SETUP → ENTRY_PENDING:  when trigger_fired()
  ENTRY_PENDING → IDLE:   when order_expired() or order_cancelled()
  ENTRY_PENDING → IN_POSITION: when order_filled()
  IN_POSITION → MANAGING: when management_conditions_met()
  IN_POSITION → EXIT_PENDING: when exit_signal()
  MANAGING → EXIT_PENDING: when exit_signal()
  EXIT_PENDING → COOLDOWN: when exit_filled()
  COOLDOWN → IDLE:        when cooldown_period_elapsed()
```

**Key property:** Every transition has a named condition. That condition is a function you can read. There is no ambiguity about what state the strategy is in at any point in time.

#### Component 3: Setup Detection

**What it does:** Identifies when market conditions match the strategy's specific pattern or structure. This is where the actual trading idea lives.

**How a discretionary trader thinks about it:** "I'm looking for a sweep of the Asian session low followed by a bullish order block formation." "I want to see price pull back to the 50 EMA and form a hammer candle." "I need to see volume divergence at a key support level."

**How it becomes code:** This is the most strategy-specific component. Every different trading idea produces different setup detection logic. But the *structure* is always the same:

```
def detect_setup(bars, indicators, market_structure):
    """
    Returns a Setup object if conditions are met, None otherwise.
    Every condition is an explicit check.
    """
    # Condition 1: Price swept a key level
    asian_low = compute_session_low(bars, session="asian")
    price_swept_low = bars[-1].low < asian_low and bars[-1].close > asian_low

    # Condition 2: Bullish structure shift
    structure = market_structure.current_bias(timeframe="5m")
    bullish_shift = structure == "bullish_shift"

    # Condition 3: Order block present
    ob = find_nearest_order_block(bars, direction="bullish", max_distance_atr=3.0)
    ob_present = ob is not None

    if price_swept_low and bullish_shift and ob_present:
        return Setup(
            direction="long",
            entry_zone=ob.zone,
            invalidation_level=asian_low - buffer,
            reason="Swept Asian low, bullish MSS, OB present"
        )

    return None
```

**Key property:** The `reason` field exists. You can always explain *why* this setup was detected. Every sub-condition is a named, testable function.

#### Component 4: Entry Logic

**What it does:** Defines exactly how and when to enter a trade once a setup is confirmed.

**Entry types (explicit codifications of what discretionary traders do):**

| Discretionary Behavior | White-Box Code Pattern |
|---|---|
| "I enter at market when I see the signal" | `submit_market_order(direction, size)` when trigger condition is true |
| "I place a limit order at the order block" | `submit_limit_order(direction, price=ob.entry_price, size)` |
| "I wait for a candle close above the level" | `if bar.close > level: submit_market_order(...)` |
| "I enter on a stop order above the high" | `submit_stop_order(direction, price=swing_high + buffer, size)` |
| "I scale in: half now, half at a better price" | `submit_market_order(size=full_size * 0.5)` then `submit_limit_order(price=better_price, size=full_size * 0.5)` |

#### Component 5: Position Sizing

**What it does:** Calculates how large the position should be. This is always a formula, never a guess.

**The universal formula (risk-based sizing):**

```
def calculate_position_size(account_equity, risk_per_trade_pct, entry_price, stop_loss_price, contract_value):
    risk_amount = account_equity * risk_per_trade_pct  # e.g., $100,000 * 0.01 = $1,000
    distance_to_stop = abs(entry_price - stop_loss_price)  # e.g., 1.1050 - 1.1020 = 0.0030
    risk_per_unit = distance_to_stop * contract_value  # e.g., 0.0030 * 100,000 = $300
    position_size = risk_amount / risk_per_unit  # e.g., $1,000 / $300 = 3.33 → 3 lots
    return floor(position_size)
```

**Key property:** Given the same inputs, this always produces the same output. No model. No learned parameter. Pure arithmetic.

#### Component 6: Exit Logic

**What it does:** Defines every way a trade can end. Discretionary traders often have vague exit rules ("I take profit when it feels extended"). White-box codification forces precision.

**Exit types that must be explicitly defined:**

| Exit Type | What It Does | Code Pattern |
|---|---|---|
| **Stop Loss (fixed)** | Hard risk limit, placed at entry | `stop_price = entry - N * ATR` |
| **Stop Loss (trailing)** | Moves with price to lock in profit | `stop_price = max(stop_price, current_price - N * ATR)` on each bar |
| **Take Profit (fixed)** | Hard target, placed at entry | `target_price = entry + R * risk_distance` where R is reward multiple |
| **Take Profit (scaled)** | Partial exits at multiple levels | `exit 50% at 1R, exit 30% at 2R, exit 20% at 3R` |
| **Time-based exit** | Close if trade hasn't moved after N bars | `if bars_in_trade > max_bars: exit_at_market()` |
| **Signal-based exit** | Close when opposing signal appears | `if opposing_setup_detected(): exit_at_market()` |
| **Structural exit** | Close when market structure breaks | `if market_structure.bias_changed(): exit_at_market()` |
| **Breakeven move** | Move stop to entry after N*R reached | `if unrealized_pnl >= 1R: stop_price = entry_price` |
| **Circuit breaker** | Stop trading after N losses in a row | `if consecutive_losses >= 3: enter_cooldown(hours=24)` |

#### Component 7: Trade Management

**What it does:** Everything that happens between entry and exit. This is where discretionary traders are often most vague ("I manage the trade based on price action") and where white-box codification adds the most value.

**Management actions that must be codified:**

```
def manage_trade(position, current_bar, bars_since_entry):
    # 1. Breakeven logic
    if position.unrealized_r >= 1.0 and not position.at_breakeven:
        position.move_stop_to(position.entry_price)
        position.at_breakeven = True

    # 2. Trailing stop logic
    if position.unrealized_r >= 2.0:
        new_stop = current_bar.close - 1.5 * ATR(14)
        if new_stop > position.current_stop:
            position.move_stop_to(new_stop)

    # 3. Partial take profit
    if position.unrealized_r >= 1.5 and not position.partial_1_taken:
        position.close_partial(fraction=0.5)
        position.partial_1_taken = True

    # 4. Time-based urgency
    if bars_since_entry > 20 and position.unrealized_r < 0.5:
        position.close_at_market(reason="Time decay, insufficient progress")
```

### 3.2 White-Box Codification Strategies

These are the specific methods you use to transform manual/discretionary logic into white-box code. Each is a different technique with different strengths.

#### Strategy A: Direct Rule Transcription

**What it is:** You take the discretionary trader's rules *exactly as stated* and write them as code, one-to-one.

**When to use it:** When the trader can articulate their rules clearly and specifically enough that each rule maps to a computable condition.

**Process:**

1. Interview the trader (or yourself). Write down every rule in natural language.
2. For each rule, identify the *observable data* it references (price, volume, time, indicator value, etc.).
3. For each rule, identify the *logical operation* (greater than, less than, crosses above, is within range, etc.).
4. For each rule, identify the *action* (enter, exit, adjust stop, do nothing, etc.).
5. Write each rule as an `if-then` statement.
6. Connect the rules into the state machine.

**Example transformation:**

| Trader says | Code becomes |
|---|---|
| "I look for price to be above the 200 EMA" | `if bar.close > EMA(close, 200):` |
| "I want RSI to be oversold" | `if RSI(close, 14) < 30:` |
| "I enter on the next candle's open" | `entry_price = next_bar.open` |
| "I put my stop below the recent swing low" | `stop = swing_low(bars, lookback=20) - atr * 0.5` |
| "I target 2:1 reward-to-risk" | `target = entry + 2 * (entry - stop)` |

**Pitfall:** Traders often say things like "I want to see strong momentum." This is not computable. You must ask: "How do you define strong? What indicator? What threshold? What timeframe?" Until every word maps to a number or a logical condition, it is not codifiable.

#### Strategy B: State Machine Extraction

**What it is:** You observe the trader's process (or your own) and identify the *states* they implicitly move through, then build a formal state machine.

**When to use it:** When the strategy has complex multi-step logic that cannot be captured by a simple list of entry/exit rules. Most ICT/SMC-style strategies, for example, have an implicit state machine: identify key level → wait for sweep → confirm structure shift → find entry zone → enter → manage.

**Process:**

1. Watch (or recall) 20+ trades. For each trade, write down every *decision point* and what happened next.
2. Group the decision points into clusters. Each cluster is a state.
3. For each state, list what events/conditions move you to the next state.
4. Draw the state machine diagram.
5. Implement each state as a class or function. Implement each transition as a condition check.

**Example state machine for an ICT-style liquidity sweep strategy:**

```
┌──────────┐   key level      ┌──────────┐   sweep         ┌──────────┐
│          │   identified     │          │   detected      │          │
│   IDLE   │ ───────────────► │ WATCHING │ ──────────────► │  SWEPT   │
│          │                  │          │                  │          │
└──────────┘                  └────┬─────┘                  └────┬─────┘
                                   │                              │
                              level becomes                  structure
                              irrelevant                     shift
                                   │                         confirmed
                                   ▼                              │
                              ┌──────────┐                        ▼
                              │   IDLE   │                   ┌──────────┐
                              └──────────┘    OB/FVG         │  SETUP   │
                                              found          │  VALID   │
                                                │            └────┬─────┘
                                                ▼                 │
                                           ┌──────────┐     price enters
                                           │  ENTRY   │     entry zone
                                           │  ZONE    │◄─────────┘
                                           └────┬─────┘
                                                │
                                           entry triggered
                                                │
                                                ▼
                                           ┌──────────┐
                                           │   IN     │
                                           │  TRADE   │
                                           └──────────┘
```

#### Strategy C: Indicator Composition

**What it is:** You combine multiple technical indicators using explicit logical operators (AND, OR, NOT) to create entry and exit conditions.

**When to use it:** When the strategy idea is fundamentally about indicator confluences. Classic examples: "MACD crossover + RSI confirmation + price above 200 MA."

**Process:**

1. List every indicator the strategy uses.
2. For each indicator, define the exact calculation (period, source, method).
3. For each indicator, define the exact condition (e.g., RSI < 30, MACD histogram > 0).
4. Define how the conditions combine (all must be true? any? weighted vote?).
5. Implement each indicator as a function. Implement the combination as a boolean expression.

**Template:**

```
def generate_signal(bars):
    # Indicator calculations - fully specified
    ema_fast = EMA(bars.close, period=9)
    ema_slow = EMA(bars.close, period=21)
    rsi = RSI(bars.close, period=14)
    atr = ATR(bars, period=14)
    volume_ratio = bars.volume[-1] / SMA(bars.volume, period=20)

    # Conditions - fully explicit
    trend_aligned = ema_fast[-1] > ema_slow[-1]
    momentum_confirmed = rsi[-1] > 50 and rsi[-1] < 70  # not overbought
    volume_sufficient = volume_ratio > 1.2
    not_overextended = bars.close[-1] < ema_fast[-1] + 2 * atr[-1]

    # Combination logic - explicit AND
    if trend_aligned and momentum_confirmed and volume_sufficient and not_overextended:
        return Signal(direction="long", strength="confirmed")

    return None
```

#### Strategy D: Structural / Price Action Codification

**What it is:** You codify concepts from price action analysis—support/resistance, supply/demand zones, chart patterns, candlestick patterns—as computable geometric or statistical conditions on price data.

**When to use it:** When the strategy is based on reading the chart rather than on indicator values. This is the hardest codification strategy because price action concepts are often described visually ("I can see a head and shoulders pattern") and must be translated into mathematical definitions.

**The critical challenge:** Price action concepts are inherently fuzzy. A "swing high" on a chart is visually obvious but computationally ambiguous. How many bars to the left and right must be lower for a bar to count as a swing high? Five? Three? Does the comparison use highs only, or closes? These decisions must be made explicit.

**Common price action concepts and their codifications:**

| Price Action Concept | Mathematical Definition |
|---|---|
| **Swing High** | A bar whose high is higher than the highs of the N bars on either side. N is a parameter (typically 2-5). |
| **Swing Low** | A bar whose low is lower than the lows of the N bars on either side. |
| **Higher High** | Current swing high > previous swing high. |
| **Lower Low** | Current swing low < previous swing low. |
| **Uptrend (by structure)** | Most recent swing high is a higher high AND most recent swing low is a higher low. |
| **Support Level** | A price zone where at least K swing lows have occurred within a range of M ATR units. K and M are parameters. |
| **Resistance Level** | Same as support, but with swing highs. |
| **Breakout** | Price closes above resistance (or below support) with volume > X * average volume. |
| **Sweep / Liquidity Grab** | Price penetrates a level by less than Y ATR units and then reverses within Z bars. |
| **Order Block** | The last opposing candle before an impulsive move of at least W ATR units. |
| **Fair Value Gap (FVG)** | Bar[i-2].low > Bar[i].high (bearish FVG) or Bar[i-2].high < Bar[i].low (bullish FVG). Three-bar pattern where the middle bar's range does not overlap with the outer bars. |
| **Change of Character (CHoCH)** | In a downtrend (lower lows, lower highs), the first higher high. Or in an uptrend, the first lower low. |
| **Break of Structure (BOS)** | In an uptrend, a new higher high that breaks the most recent swing high. Continuation signal. |

#### Strategy E: Regime-Conditional Rule Sets

**What it is:** You define multiple sets of rules and select which set to use based on a classified market regime. The regime classification itself is rule-based (making it fully white-box) or model-based (making it hybrid—see Section 5).

**When to use it:** When you recognize that your strategy works in some market conditions but not others. Classic example: a trend-following strategy that hemorrhages money during ranges.

**Process:**

1. Define the regimes you believe exist (e.g., trending, ranging, volatile, quiet).
2. Define explicit rules for classifying the current regime.
3. Define a separate rule set for each regime (or define which regimes the strategy sits out).

```
def classify_regime(bars, indicators):
    adx = ADX(bars, period=14)
    atr_ratio = ATR(bars, 5) / ATR(bars, 50)  # short-term vs long-term volatility

    if adx[-1] > 25 and atr_ratio > 1.2:
        return "TRENDING_VOLATILE"
    elif adx[-1] > 25 and atr_ratio <= 1.2:
        return "TRENDING_QUIET"
    elif adx[-1] <= 25 and atr_ratio > 1.2:
        return "RANGING_VOLATILE"
    else:
        return "RANGING_QUIET"

def select_strategy(regime):
    if regime == "TRENDING_VOLATILE":
        return TrendFollowingStrategy(trail_multiplier=3.0)
    elif regime == "TRENDING_QUIET":
        return TrendFollowingStrategy(trail_multiplier=1.5)
    elif regime == "RANGING_VOLATILE":
        return None  # sit out
    elif regime == "RANGING_QUIET":
        return MeanReversionStrategy(entry_zscore=2.0)
```

### 3.3 Complete White-Box Strategy Template

This template can be used as a starting skeleton for any white-box strategy. Fill in the specific logic for your idea.

```python
class WhiteBoxStrategy:
    """
    Complete white-box strategy template.
    Every decision is an explicit, inspectable rule.
    """

    # ── CONFIGURATION (all parameters are named and documented) ──
    config = {
        "name": "Strategy Name",
        "version": "1.0",
        "instruments": ["EURUSD"],
        "timeframe": "5m",
        "session_filter": ["london", "new_york"],
        "risk_per_trade_pct": 0.01,
        "max_concurrent_trades": 1,
        "max_daily_loss_pct": 0.03,
        "cooldown_after_loss_bars": 12,
        # ... strategy-specific parameters
    }

    # ── STATE ──
    state = "IDLE"  # IDLE | SETUP | ENTRY_PENDING | IN_POSITION | COOLDOWN

    # ── CONTEXT FILTER ──
    def is_context_valid(self, bar, daily_bars, calendar):
        """
        Outermost gate. Returns False if the strategy should not be
        active at all right now. Every condition is explicit.
        """
        # ... session check, news check, daily loss check, etc.
        pass

    # ── REGIME CLASSIFICATION (optional, white-box version) ──
    def classify_regime(self, bars):
        """
        Returns a string label for the current market regime.
        All classification logic is explicit rules, not a trained model.
        """
        pass

    # ── SETUP DETECTION ──
    def detect_setup(self, bars, indicators, structure):
        """
        Returns a Setup object if conditions are met, None otherwise.
        The Setup object contains: direction, entry_zone, invalidation,
        reason (human-readable explanation of why this is a setup).
        """
        pass

    # ── ENTRY LOGIC ──
    def plan_entry(self, setup, current_bar):
        """
        Given a valid setup, returns an Order object specifying
        order type, price, size, and expiry conditions.
        """
        pass

    # ── POSITION SIZING ──
    def calculate_size(self, entry_price, stop_price, account_equity):
        """
        Pure arithmetic. Given risk parameters, returns position size.
        """
        pass

    # ── EXIT LOGIC ──
    def check_exit(self, position, current_bar, bars_since_entry):
        """
        Checks all exit conditions. Returns an ExitSignal if any
        condition is met, None otherwise. Exit conditions are
        checked in priority order.
        """
        pass

    # ── TRADE MANAGEMENT ──
    def manage_position(self, position, current_bar, bars_since_entry):
        """
        Adjusts stops, takes partials, moves to breakeven.
        All adjustments are explicit rules.
        """
        pass

    # ── STATE TRANSITION ──
    def update(self, bar, account):
        """
        Main loop. Called on each new bar.
        Manages state transitions based on current state and conditions.
        """
        if not self.is_context_valid(bar, ...):
            return

        if self.state == "IDLE":
            setup = self.detect_setup(...)
            if setup:
                self.state = "SETUP"
                self.current_setup = setup

        elif self.state == "SETUP":
            if self.setup_still_valid(self.current_setup, bar):
                if self.trigger_fired(self.current_setup, bar):
                    order = self.plan_entry(self.current_setup, bar)
                    self.submit_order(order)
                    self.state = "ENTRY_PENDING"
            else:
                self.state = "IDLE"

        elif self.state == "ENTRY_PENDING":
            if self.order_filled():
                self.state = "IN_POSITION"
            elif self.order_expired():
                self.state = "IDLE"

        elif self.state == "IN_POSITION":
            exit_signal = self.check_exit(self.position, bar, ...)
            if exit_signal:
                self.close_position(exit_signal.reason)
                self.state = "COOLDOWN"
            else:
                self.manage_position(self.position, bar, ...)

        elif self.state == "COOLDOWN":
            if self.cooldown_elapsed():
                self.state = "IDLE"

    # ── LOGGING / EXPLAINABILITY ──
    def explain_last_trade(self):
        """
        Returns a human-readable explanation of the last trade:
        why it was taken, what the setup was, what the exit reason was.
        This is trivial in a white-box strategy because every decision
        has an explicit reason.
        """
        pass
```

---

## 4. Black-Box Strategies: Complete Reference

### 4.1 The Anatomy of a Black-Box Strategy

A black-box strategy replaces the explicit rules of a white-box strategy with trained models. The structural components still exist, but their internal logic is learned from data rather than written by a human.

#### Component 1: Feature Engineering Pipeline

**What it replaces:** In a white-box strategy, the human decides what data to look at (price, volume, indicators). In a black-box strategy, the feature engineering pipeline is the equivalent—but it is often much broader, feeding the model hundreds or thousands of input features, many of which a human would never think to combine.

**What it does:** Transforms raw market data into a matrix of numbers that the model consumes.

**Common feature categories:**

| Category | Examples |
|---|---|
| **Price-derived** | Returns over multiple lookbacks (1, 5, 10, 20, 60, 120 bars), log returns, normalized price relative to moving averages, distance from N-day high/low |
| **Volume-derived** | Volume ratio vs N-period average, volume-weighted price deviation, buy/sell volume imbalance, cumulative delta |
| **Volatility-derived** | ATR at multiple periods, realized volatility, Garman-Klass volatility, ratio of short-term to long-term volatility, VIX term structure |
| **Microstructure** | Bid-ask spread, order book depth, trade flow imbalance, time between trades, quote-to-trade ratio |
| **Cross-asset** | Correlation with related assets over rolling windows, spread to benchmark, sector-relative momentum |
| **Calendar/temporal** | Day of week, hour of day, days until options expiry, days since last Fed meeting, quarter-end proximity |
| **Sentiment/text** | NLP-derived sentiment score from news headlines, earnings call tone, social media mention velocity |
| **Macro** | Yield curve slope, credit spreads, inflation expectations, PMI momentum |

**Critical point:** The choice of features is still a human decision, even in a black-box system. Bad features → bad model, no matter how sophisticated the architecture. Feature engineering is where domain knowledge enters a black-box strategy.

```python
class FeaturePipeline:
    """
    Transforms raw OHLCV + auxiliary data into a feature matrix.
    This is the human-designed part of a black-box strategy.
    """
    def compute_features(self, bars, auxiliary_data):
        features = {}

        # Price features
        for lookback in [1, 5, 10, 20, 60]:
            features[f"return_{lookback}"] = bars.close[-1] / bars.close[-1-lookback] - 1
            features[f"high_ratio_{lookback}"] = bars.close[-1] / max(bars.high[-lookback:])
            features[f"low_ratio_{lookback}"] = bars.close[-1] / min(bars.low[-lookback:])

        # Volatility features
        features["atr_5"] = ATR(bars, 5)[-1]
        features["atr_20"] = ATR(bars, 20)[-1]
        features["vol_ratio"] = features["atr_5"] / features["atr_20"]

        # Volume features
        features["volume_ratio"] = bars.volume[-1] / SMA(bars.volume, 20)[-1]

        # ... potentially hundreds more

        return features
```

#### Component 2: Model (The "Black Box" Itself)

**What it replaces:** The setup detection, entry logic, and sometimes exit logic of a white-box strategy. Instead of `if condition_A and condition_B then enter`, the model outputs a score/prediction that is thresholded into a decision.

**Common model architectures used in trading:**

| Architecture | What It Does | When It's Used |
|---|---|---|
| **Gradient Boosted Trees (XGBoost, LightGBM, CatBoost)** | Takes a row of features, passes it through an ensemble of decision trees, outputs a prediction. The trees were constructed by the training algorithm to minimize prediction error on historical data. | Most common for tabular features (one row per bar). Strong baseline. Often used for daily/weekly signals. |
| **LSTM (Long Short-Term Memory)** | A recurrent neural network that processes sequences. It reads features bar by bar, maintaining a hidden state that "remembers" relevant patterns from previous bars. | When the temporal sequence matters. The order of bars carries information beyond what individual-bar features capture. |
| **Transformer** | Attention-based architecture that processes all bars in a window simultaneously and learns which bars are most relevant to the current prediction. | When long-range dependencies matter and you have sufficient data. Increasingly used in medium-frequency strategies. |
| **CNN (Convolutional Neural Network)** | Treats a window of price/feature data like an image and detects local patterns (similar to chart pattern recognition). | When local price patterns (candlestick formations, short-term momentum shapes) are the primary signal source. |
| **Random Forest** | Ensemble of decision trees, each trained on a random subset of data and features. Prediction is the average (regression) or majority vote (classification) of all trees. | Simpler alternative to gradient boosting. More resistant to overfitting on small datasets. |
| **Reinforcement Learning Agent (DQN, PPO, A2C)** | Learns a *policy*: given the current state (features + position), what action to take (buy, sell, hold, size). Learns by trial and error in a simulated market. | When the strategy involves multi-step decisions (entry + management + exit) that are hard to decompose. Also used for execution optimization (minimizing market impact). |

**How the model makes a trade decision:**

```python
class BlackBoxSignalGenerator:
    def __init__(self, model_path):
        self.model = load_model(model_path)  # Pre-trained model
        self.threshold_long = 0.65   # Only go long if model confidence > 65%
        self.threshold_short = 0.35  # Only go short if model confidence < 35%

    def generate_signal(self, features):
        """
        The model takes in a feature vector and outputs a number.
        The internal computation involves thousands of learned weights
        that a human did not set. This is the 'black box.'
        """
        prediction = self.model.predict(features)
        # prediction might be: probability of price going up in next N bars

        if prediction > self.threshold_long:
            return Signal(direction="long", confidence=prediction)
        elif prediction < self.threshold_short:
            return Signal(direction="short", confidence=1 - prediction)
        else:
            return None  # No signal - model is not confident enough
```

**What you can see:** inputs (features) and outputs (prediction score). **What you cannot see (or cannot meaningfully interpret):** the thousands of intermediate computations that produced that score.

#### Component 3: Training Pipeline

**What it is:** The process by which the model's weights are learned from historical data. This is the most critical and most dangerous part of a black-box strategy because it is where overfitting, data leakage, and survivorship bias can silently destroy the strategy's validity.

**The training pipeline must answer these questions:**

1. **What is the target variable?** What are you training the model to predict?
   - Future return over the next N bars (regression)
   - Whether price will be up or down in N bars (classification)
   - Whether a trade with a specific stop/target would be profitable (classification)
   - Optimal action to take (reinforcement learning)

2. **How is the data split?** You must never test on data the model has seen during training.
   - **Temporal split (mandatory for time series):** Train on 2010-2018, validate on 2019-2020, test on 2021-2023. Never shuffle time-series data randomly.
   - **Walk-forward validation:** Train on years 1-3, test on year 4. Then train on years 1-4, test on year 5. And so on. This simulates how the model would have been used in real time.
   - **Purging and embargoing:** Remove data points near the boundary between train and test sets to prevent leakage from overlapping labels.

3. **How do you prevent overfitting?**
   - Regularization (L1, L2, dropout)
   - Early stopping (stop training when validation loss stops improving)
   - Feature selection (remove features that don't improve out-of-sample performance)
   - Ensemble methods (combine multiple models to reduce variance)
   - Cross-validation with purging

4. **How do you detect data leakage?**
   - If your model's in-sample accuracy is 95% but out-of-sample accuracy is 52%, you have leakage or overfitting.
   - Common sources: using future data in feature computation (e.g., a centered moving average), including the target in the features, not accounting for the time lag between when data is published and when it was available.

```python
class TrainingPipeline:
    def train_and_validate(self, all_data, feature_pipeline):
        # 1. Split data temporally
        train_data = all_data["2010":"2018"]
        val_data = all_data["2019":"2020"]
        test_data = all_data["2021":"2023"]

        # 2. Compute features and labels
        X_train = feature_pipeline.compute_features(train_data)
        y_train = self.compute_labels(train_data, horizon=10, method="binary_return")

        X_val = feature_pipeline.compute_features(val_data)
        y_val = self.compute_labels(val_data, horizon=10, method="binary_return")

        # 3. Train model with early stopping based on validation performance
        model = LightGBM(n_estimators=1000, learning_rate=0.01, max_depth=5)
        model.fit(
            X_train, y_train,
            eval_set=(X_val, y_val),
            early_stopping_rounds=50,
            verbose=False
        )

        # 4. Evaluate on held-out test set (only done ONCE, at the very end)
        X_test = feature_pipeline.compute_features(test_data)
        y_test = self.compute_labels(test_data, horizon=10, method="binary_return")
        test_predictions = model.predict(X_test)

        # 5. Compute metrics
        accuracy = compute_accuracy(y_test, test_predictions)
        sharpe = compute_sharpe(y_test, test_predictions, transaction_costs=True)

        return model, {"accuracy": accuracy, "sharpe": sharpe}
```

#### Component 4: Inference and Execution

**What it does:** Takes the trained model and uses it in real-time (or in backtesting) to generate actual trades.

```python
class BlackBoxExecutor:
    def __init__(self, model, feature_pipeline, risk_manager):
        self.model = model
        self.feature_pipeline = feature_pipeline
        self.risk_manager = risk_manager  # Risk management can still be white-box!

    def on_new_bar(self, bar, account):
        features = self.feature_pipeline.compute_features(bar)
        signal = self.model.predict(features)

        if signal > self.threshold_long and self.risk_manager.can_trade(account):
            size = self.risk_manager.calculate_size(account, ...)
            self.submit_order("long", size)

        # Note: even in a black-box strategy, risk management
        # (position sizing, max drawdown limits, etc.) is often
        # still white-box. You don't want a neural network deciding
        # how much to risk.
```

#### Component 5: Model Lifecycle Management

**What it is:** The ongoing process of monitoring, retraining, and replacing models over time. This is the most operationally complex part of running a black-box strategy and has no equivalent in white-box strategies.

**Why it's needed:** Unlike explicit rules, which stay the same unless you change them, models degrade over time because the statistical patterns they learned may shift (concept drift, regime change, structural market changes).

**Lifecycle stages:**

1. **Monitoring:** Track the model's live predictions against actual outcomes. Compute rolling accuracy, Sharpe ratio, calibration (does "70% confidence" actually mean "right 70% of the time"?).
2. **Drift detection:** Compare the distribution of incoming features to the training distribution. If they diverge significantly, the model may be operating outside its learned domain.
3. **Retraining schedule:** Retrain the model periodically (daily, weekly, monthly) on updated data, using the same pipeline with the same validation discipline.
4. **Model comparison:** Before deploying a retrained model, compare it to the existing model on recent data. Only deploy if the new model is better by a meaningful margin.
5. **Rollback:** If a newly deployed model performs poorly in live trading, roll back to the previous model automatically.

### 4.2 Black-Box Codification Strategies

These are the specific methods for transforming a manual/discretionary trading idea into a black-box strategy.

#### Strategy A: Supervised Learning on Labeled Trades

**What it is:** You take a collection of the discretionary trader's past trades (with their entries, exits, and outcomes), extract features from the market data at the time of each trade, and train a model to predict trade outcomes or to predict when the trader would take a trade.

**Process:**

1. Collect a dataset of historical trades: timestamp, direction, entry price, exit price, outcome (win/loss/R-multiple).
2. For each trade, go to the historical market data at that timestamp and compute a broad set of features (price features, volume features, volatility, etc.).
3. Create a binary label: 1 = trade was profitable, 0 = trade was not.
4. Train a classifier (XGBoost, random forest, neural network) to predict the label from the features.
5. The trained model can now score any future market moment: "Would this have been a good trade for this discretionary trader?"

**Key insight:** You are not codifying the *rules*. You are codifying the *outcomes*. The model reverse-engineers the trader's edge from the data.

**Risk:** If the trader's edge was based on real-time information not captured in the features (e.g., they were watching the order book, or they had a "feel" from watching the tape), the model will fail because the relevant inputs are missing.

#### Strategy B: Pattern Prediction from Time Series

**What it is:** You frame the trading problem as a time-series prediction problem. Given a window of recent market data, predict what happens next (price direction, volatility, return distribution).

**Process:**

1. Define the prediction target: "Will price be higher or lower 10 bars from now?"
2. Create a sliding window of features: the last N bars of OHLCV data, indicator values, etc.
3. Train a sequence model (LSTM, Transformer, temporal CNN) to map the window to the prediction.
4. At runtime, feed the model the current window and use its prediction to generate a trading signal.

**Architecture decision: how to represent the input window:**

| Approach | Description |
|---|---|
| **Tabular features per window** | Compute summary statistics over the window (mean return, max drawdown, trend slope, etc.) and feed them as a flat vector to a gradient boosted model. Fast to train, harder to capture complex sequential patterns. |
| **Raw OHLCV sequence** | Feed the raw bars as a 2D matrix (N bars × 5 channels) to an LSTM or Transformer. Lets the model learn its own features. Requires much more data. |
| **Engineered sequence** | Compute per-bar features (return, volume ratio, RSI value, etc.) and feed the sequence of feature vectors to a sequence model. Middle ground: some human knowledge in feature design, but the model learns temporal patterns. |

#### Strategy C: Reinforcement Learning for Full Strategy

**What it is:** Instead of predicting price (which is a means to an end), you train an agent to directly learn the optimal trading policy: given the current market state and current position, what action maximizes cumulative risk-adjusted return?

**Process:**

1. Define the state space: what information the agent sees (features, current position, unrealized P&L, time of day, etc.).
2. Define the action space: what the agent can do (buy, sell, hold, adjust size, set stop level).
3. Define the reward function: what the agent optimizes for (P&L, Sharpe ratio, P&L minus transaction costs, etc.).
4. Build a simulation environment that replays historical market data and executes the agent's actions.
5. Train the agent using a reinforcement learning algorithm (PPO, A2C, DQN, SAC).
6. Validate extensively: the agent can overfit to the training environment if the simulation is unrealistic or if the data is reused too many times.

**Key advantage:** The agent learns entry, management, and exit as a single integrated policy, not as separate components. It can learn behaviors that are hard to specify as rules (e.g., "hold through a temporary drawdown if the pattern suggests a continuation").

**Key danger:** RL is the hardest approach to validate because the agent can learn to exploit simulator artifacts (e.g., unrealistic fill assumptions) rather than genuine market patterns.

#### Strategy D: NLP-Driven Signal Generation

**What it is:** Use natural language processing models to extract trading signals from text data (news, earnings calls, central bank statements, social media, SEC filings).

**Process:**

1. Collect a corpus of text data time-stamped to market events.
2. Define the label: what happened to the relevant asset after this text was published.
3. Train or fine-tune an NLP model (BERT, FinBERT, GPT-based classifier) to score text as bullish/bearish/neutral.
4. At runtime, ingest text in real time, score it, and generate signals.

**Example:** A model reads the first sentence of a Fed press release—"The Committee decided to raise the target range for the federal funds rate by 75 basis points"—and within milliseconds classifies it as "hawkish, magnitude: large." This triggers pre-programmed trades (short bonds, long USD).

#### Strategy E: Statistical Arbitrage

**What it is:** Find groups of assets whose prices have a stable mathematical relationship, and trade deviations from that relationship.

**Process:**

1. Identify candidate pairs/baskets (same sector, same business, economic substitutes).
2. Test for cointegration: are the assets statistically bound to revert to a common equilibrium?
3. Compute the spread (the difference or ratio between the assets' prices).
4. Fit a mean-reversion model to the spread.
5. When the spread deviates by more than N standard deviations, enter a trade betting on reversion.

**Why it's black-box:** While the concept is simple, real implementations use models (Kalman filters, VECM, neural networks) to dynamically estimate the hedge ratio, the equilibrium level, and the expected reversion speed. These models have learned parameters that are not transparently set by a human.

### 4.3 What Remains White-Box Even in Black-Box Strategies

This is a critical and often-overlooked point. Even in the most purely black-box strategies at the most sophisticated quant firms, certain components are almost always kept explicitly rule-based:

| Component | Why It Stays White-Box |
|---|---|
| **Risk management** | You never want a neural network deciding how much of your capital to risk. Position sizing, maximum drawdown limits, correlation-based portfolio constraints, and kill switches are explicit rules. If the risk system is opaque, a model error can bankrupt you. |
| **Execution constraints** | Order types, maximum order sizes, slippage assumptions, and market-hour restrictions are hard-coded rules. |
| **Universe selection** | Which instruments to trade is usually a rule-based decision (minimum liquidity, minimum market cap, exchange membership, etc.). |
| **Circuit breakers** | "If the strategy loses more than X% in a day, stop trading" is always an explicit rule. No model should be allowed to override this. |

---

## 5. Hybrid Strategies: Complete Reference

### 5.1 Why Hybrid Is Often the Best Practical Choice

Pure white-box strategies are limited by the human's ability to notice patterns and specify them precisely. Pure black-box strategies are limited by data quality, overfitting risk, and the inability to incorporate domain knowledge that hasn't been seen in historical data. Hybrid strategies take the best of both worlds:

- **Human domain knowledge** provides the structural framework, ensures the strategy makes conceptual sense, and prevents catastrophically stupid trades.
- **Statistical/ML methods** fine-tune parameters, detect regimes, filter noise, and capture subtle patterns the human missed.

### 5.2 Hybrid Architecture Patterns

#### Pattern 1: White-Box Structure + Statistically Optimized Parameters

**Concept:** The strategy logic is entirely explicit (all rules are written by a human), but the specific parameter values (indicator periods, thresholds, multipliers) are found by systematic optimization rather than by human judgment.

**Example:**

The human writes:
- "Enter long when fast EMA crosses above slow EMA."
- "Only enter if ADX > threshold."
- "Stop loss at N × ATR below entry."
- "Take profit at M × ATR above entry."

The optimization process finds:
- fast EMA period = 12 (tested 5-50)
- slow EMA period = 34 (tested 20-200)
- ADX threshold = 22 (tested 15-40)
- N = 1.8 (tested 0.5-4.0)
- M = 3.2 (tested 1.0-6.0)

**What makes it hybrid, not white-box:** The parameters were not chosen by human reasoning ("I think 12 and 34 are good periods because..."). They were chosen because they produced the best results on historical data. This introduces the risk of parameter overfitting (the values might work on historical data but fail on future data).

**Validation discipline required:**
- Walk-forward optimization (optimize on rolling windows, test on the next window)
- Parameter stability analysis (do nearby parameter values produce similar results? If `fast_ema=12` works but `fast_ema=11` and `fast_ema=13` fail badly, the edge is fragile and probably overfit)
- Out-of-sample hold-out (never optimize on the final test period)

```python
class HybridOptimizedStrategy:
    """
    Rules are white-box. Parameters are found by optimization.
    """
    def __init__(self, optimized_params):
        # These params came from a walk-forward optimization
        self.fast_period = optimized_params["fast_ema"]
        self.slow_period = optimized_params["slow_ema"]
        self.adx_threshold = optimized_params["adx_threshold"]
        self.stop_atr_mult = optimized_params["stop_atr_mult"]
        self.target_atr_mult = optimized_params["target_atr_mult"]

    def generate_signal(self, bars):
        # Logic is fully explicit and readable
        fast_ema = EMA(bars.close, self.fast_period)
        slow_ema = EMA(bars.close, self.slow_period)
        adx = ADX(bars, 14)

        if fast_ema[-1] > slow_ema[-1] and fast_ema[-2] <= slow_ema[-2]:
            if adx[-1] > self.adx_threshold:
                return Signal("long")
        return None
```

#### Pattern 2: White-Box Entry + ML Confirmation Filter

**Concept:** The entry signal comes from explicit rules (the human's trading idea). But before the trade is taken, an ML model evaluates the setup and assigns a probability score. The trade is only taken if the model's confidence exceeds a threshold.

**Why this works well:**

- The white-box entry ensures you only take trades that make structural/conceptual sense.
- The ML filter eliminates the subset of those trades that historically have low probability of success, based on context the rules don't capture (e.g., "this setup pattern works 60% of the time overall, but in the current volatility/volume/correlation regime, it only works 35% of the time").

```python
class HybridFilteredStrategy:
    def __init__(self, confirmation_model):
        self.model = confirmation_model  # Pre-trained ML model
        self.min_confidence = 0.60

    def on_bar(self, bar, bars_history, account):
        # Step 1: White-box setup detection (fully explicit)
        setup = self.detect_setup_whitebox(bars_history)
        if setup is None:
            return  # No trade idea

        # Step 2: ML confirmation (black-box filter)
        features = self.extract_context_features(bars_history, setup)
        confidence = self.model.predict_proba(features)

        if confidence >= self.min_confidence:
            # Step 3: White-box execution
            entry_order = self.plan_entry(setup, bar)
            size = self.calculate_size(...)  # White-box sizing
            self.submit(entry_order, size)
        else:
            self.log(f"Setup detected but filtered by ML: confidence={confidence:.2f}")
```

#### Pattern 3: ML Regime Classification + White-Box Regime-Specific Rules

**Concept:** A trained model (often a Hidden Markov Model) classifies the current market regime. The strategy then selects from a set of pre-defined, explicit rule sets based on the classified regime.

**Why this is powerful:**

Many strategies fail not because their rules are wrong, but because they are applied in the wrong regime. A trend-following strategy applied during a range-bound market will lose money. If you can accurately classify the regime, you can deploy the right strategy for the right conditions.

**Hidden Markov Models (HMMs) in detail:**

An HMM is the most common model for regime classification. Here's how it works:

- **Hidden states:** The "true" market regime (e.g., "bull trend," "bear trend," "high-vol range," "low-vol range"). These are "hidden" because you never directly observe them. You infer them from observable data.
- **Observations:** What you can see—returns, volatility, volume, spreads.
- **Transition matrix:** The probability of moving from one regime to another. Learned from data. Example: P(staying in bull trend | currently in bull trend) = 0.95. P(transitioning from bull trend to bear trend) = 0.02.
- **Emission matrix:** The probability of observing certain data given you are in a certain regime. Example: In the "high-vol range" regime, daily returns are drawn from N(0, 0.025). In the "low-vol bull" regime, daily returns are drawn from N(0.001, 0.008).
- **Inference:** Given the sequence of observations, the HMM uses the Viterbi algorithm or forward-backward algorithm to calculate the probability of being in each hidden state at each point in time.

```python
class HybridRegimeStrategy:
    def __init__(self, hmm_model, strategy_map):
        self.hmm = hmm_model  # Trained Hidden Markov Model
        self.strategy_map = strategy_map  # {regime_label: WhiteBoxStrategy}

    def on_bar(self, bar, bars_history, account):
        # Step 1: ML regime classification (black-box)
        recent_returns = compute_returns(bars_history, lookback=60)
        recent_vol = compute_rolling_vol(bars_history, lookback=20)
        observations = np.column_stack([recent_returns, recent_vol])

        regime_probs = self.hmm.predict_proba(observations)
        # regime_probs might be: {"bull_trend": 0.72, "bear_trend": 0.05,
        #                         "high_vol_range": 0.18, "low_vol_range": 0.05}

        current_regime = max(regime_probs, key=regime_probs.get)
        regime_confidence = regime_probs[current_regime]

        if regime_confidence < 0.60:
            return  # Regime uncertain, sit out

        # Step 2: Select white-box strategy for this regime
        active_strategy = self.strategy_map.get(current_regime)
        if active_strategy is None:
            return  # No strategy for this regime (intentionally sitting out)

        # Step 3: Run the white-box strategy
        active_strategy.on_bar(bar, bars_history, account)
```

#### Pattern 4: White-Box Signal + ML-Optimized Execution

**Concept:** The trading decision (what to trade, when, in which direction) is white-box. But the execution (how to fill the order without moving the market) is optimized by a black-box model—typically a Reinforcement Learning agent.

**Why it matters:** For institutional-size orders, naive execution (placing a single large market order) creates adverse market impact—you push the price against yourself. Smart execution splits the order into many small pieces, varying the timing and size to minimize this impact.

**This is the Markov Decision Process (MDP) / Reinforcement Learning use case:**

- **State:** Current fill percentage, time elapsed, current spread, recent volume, volatility.
- **Action:** Place a limit order at a certain distance from mid-price, or place a market order of a certain size, or wait.
- **Reward:** Negative market impact (lower is better). Measured as the difference between the average fill price and the price at the time the order was initiated.

```python
class HybridExecutionStrategy:
    """
    White-box signal + RL-optimized execution
    """
    def __init__(self, signal_strategy, execution_agent):
        self.signal_strategy = signal_strategy  # White-box: decides WHAT to trade
        self.execution_agent = execution_agent  # RL agent: decides HOW to execute

    def on_signal(self, signal, account):
        # White-box: decide the trade
        target_position = signal.direction
        target_size = self.calculate_size(...)  # White-box sizing

        # Black-box: execute optimally
        # The RL agent splits the order and manages execution
        self.execution_agent.execute(
            target_size=target_size,
            direction=target_position,
            urgency="medium",  # Human-set parameter
            max_time_minutes=30  # Human-set constraint
        )
```

#### Pattern 5: White-Box Candidate Generation + ML Ranking

**Concept:** The white-box system generates a list of candidate trades (setups that meet all the explicit criteria). The ML model then ranks them by expected quality, and only the top-ranked candidates are traded.

**When to use this:** When your strategy generates more setups than you can (or should) trade simultaneously. You need a way to pick the best ones.

```python
class HybridRankedStrategy:
    def on_bar(self, bar, bars_history, account):
        # White-box: generate all valid setups
        all_setups = []
        for instrument in self.universe:
            setup = self.detect_setup(instrument, bars_history)
            if setup is not None:
                all_setups.append(setup)

        if not all_setups:
            return

        # Black-box: rank setups by predicted quality
        ranked = []
        for setup in all_setups:
            features = self.extract_setup_features(setup, bars_history)
            score = self.ranking_model.predict(features)
            ranked.append((setup, score))

        ranked.sort(key=lambda x: x[1], reverse=True)

        # White-box: take the top N, respecting risk limits
        for setup, score in ranked[:self.max_concurrent]:
            if score > self.min_score and self.risk_manager.can_trade(account):
                self.enter_trade(setup)
```

#### Pattern 6: Ensemble of White-Box Strategies + Meta-Learner

**Concept:** Multiple white-box strategies run independently, each generating signals. A meta-learning model (trained on historical performance of each strategy across different conditions) decides how much weight to give each strategy's signal at any given time.

```python
class HybridEnsemble:
    def __init__(self, strategies, meta_model):
        self.strategies = strategies  # List of white-box strategies
        self.meta_model = meta_model  # Trained model that assigns weights

    def on_bar(self, bar, bars_history, account):
        # Collect signals from all white-box strategies
        signals = {}
        for strategy in self.strategies:
            signal = strategy.generate_signal(bars_history)
            signals[strategy.name] = signal  # Signal might be +1, 0, -1

        # Meta-model assigns dynamic weights based on current regime
        regime_features = self.extract_regime_features(bars_history)
        weights = self.meta_model.predict_weights(regime_features)
        # weights might be: {"trend_follower": 0.6, "mean_reversion": 0.1, "breakout": 0.3}

        # Compute weighted consensus signal
        composite_signal = sum(
            weights[s.name] * signals[s.name]
            for s in self.strategies
            if signals[s.name] is not None
        )

        if composite_signal > self.threshold:
            self.enter_trade("long", ...)
        elif composite_signal < -self.threshold:
            self.enter_trade("short", ...)
```

---

## 6. The Universal Transformation Process

This section provides a step-by-step process for taking **any** manual/discretionary trading strategy and transforming it into code. The process works regardless of whether you're building a white-box, black-box, or hybrid strategy.

### Step 1: Extract the Idea Core

Before writing any code, you must answer these questions about the manual strategy. If you cannot answer them clearly, you are not ready to codify.

| Question | Why It Matters |
|---|---|
| **What is the edge hypothesis?** What do you believe is the reason this strategy makes money? | Determines whether you need white-box (edge is structural/causal) or black-box (edge is statistical/correlational). |
| **What asset(s) does it trade?** | Determines data requirements. |
| **What timeframe(s) does it operate on?** | Determines bar frequency, feature lookback windows, and expected trade duration. |
| **What does a setup look like?** Can you describe it in words? Can you draw it? | If you can describe it as rules → white-box. If you can only say "I know it when I see it" → you need black-box or more analysis. |
| **What triggers the entry?** After the setup is present, what specific thing makes you pull the trigger? | Must be a specific observable event, not "when it feels right." |
| **Where does the stop go?** If you're wrong, at what point do you know you're wrong? | Must be a specific price or condition. |
| **Where does the target go?** How do you decide when to take profit? | Specific price, or specific condition (e.g., opposing signal). |
| **When do you NOT trade this strategy?** What market conditions make it fail? | Defines the context filter and potential regime filter. |
| **How many trades does it take per day/week/month?** | Determines whether you have enough data to train a model (for black-box). |
| **What information do you use that is NOT on the chart?** News, order flow, gut feeling? | Determines what additional data sources are needed. |

### Step 2: Choose Your Codification Approach

Use this decision tree:

```
Can you describe EVERY condition of the strategy as a specific,
computable rule (price > X, indicator > Y, time is between A and B)?
│
├── YES → Can you also specify the exact parameter values with confidence?
│   │
│   ├── YES → FULL WHITE-BOX (Section 3)
│   │         Write the rules and parameters directly as code.
│   │
│   └── NO  → HYBRID Pattern 1: White-box rules + optimized parameters
│             Write the rules, then systematically optimize the parameters.
│
└── NO  → Can you describe the STRUCTURE but not the detailed conditions?
    │      (e.g., "I look for sweeps of key levels" but you can't fully
    │       define what a 'key level' is computationally)
    │
    ├── YES → HYBRID Pattern 2 or 3
    │         Write what you can as rules. Use ML for the parts you
    │         can't fully specify.
    │
    └── NO  → Can you at least provide a dataset of past trades
              with outcomes?
        │
        ├── YES → BLACK-BOX Strategy A: Supervised learning on labeled trades
        │         Train a model to replicate your edge from the outcomes.
        │
        └── NO  → You probably need to do more analysis before codifying.
                  Go back and study 50+ examples of the setup. Take notes.
                  After that, re-enter this decision tree.
```

### Step 3: Decompose into Components

Regardless of your approach, decompose the strategy into these universal components:

| Component | White-Box Implementation | Black-Box Implementation | Hybrid Implementation |
|---|---|---|---|
| **Universe/Instrument Selection** | Explicit list or rule-based filter | Rule-based filter (almost always white-box) | Rule-based filter |
| **Context/Session Filter** | Explicit time and condition checks | Usually white-box, sometimes model-based | White-box |
| **Regime Classification** | Rule-based (ADX, volatility ratios) | HMM, neural network classifier | HMM or ML classifier + white-box regime-specific rules |
| **Setup Detection** | Explicit pattern matching | Trained model (classifier) | White-box pattern + ML confidence filter |
| **Entry Trigger** | Specific price action or indicator condition | Model output > threshold | White-box trigger, possibly ML-gated |
| **Entry Execution** | Simple order placement | Possibly RL-optimized execution | White-box for small size, RL for large size |
| **Position Sizing** | Formula-based (always white-box) | Formula-based (always white-box) | Formula-based (always white-box) |
| **Stop Loss** | Fixed or rule-based | Can be model-proposed, but hard limits always white-box | White-box placement, possibly model-adjusted |
| **Take Profit** | Fixed or rule-based | Model-proposed | White-box levels, possibly model-ranked |
| **Trade Management** | Explicit rules for trailing, partials, breakeven | RL agent policy | White-box rules, model-informed adjustments |
| **Exit Logic** | Explicit conditions | Model signal or RL action | White-box exits + model-suggested dynamic exits |
| **Risk Management** | Explicit rules (ALWAYS) | Explicit rules (ALWAYS) | Explicit rules (ALWAYS) |
| **Circuit Breakers** | Explicit rules (ALWAYS) | Explicit rules (ALWAYS) | Explicit rules (ALWAYS) |

### Step 4: Implement the Data Layer

Before writing any strategy logic, you need the data infrastructure. What data does your strategy need?

```
Minimum (every strategy):
  - OHLCV bars at the strategy's timeframe
  - Account state (equity, open positions, daily P&L)

Common additions:
  - Higher-timeframe bars (for trend filters, structure analysis)
  - Tick data or sub-bar data (for order flow features)
  - Volume profile data
  - Economic calendar
  - Instrument specifications (contract size, tick value, margin requirements)

Black-box additions:
  - Feature store (pre-computed features at various lookbacks)
  - Alternative data (news sentiment, social media, satellite, etc.)
  - Cross-asset data (correlated instruments, indices, sectors)
```

### Step 5: Implement, Test, Validate

| Phase | White-Box | Black-Box | Hybrid |
|---|---|---|---|
| **Implementation** | Write the state machine, indicators, and rules | Build feature pipeline, train model, build inference engine | Write rules for the explicit parts, train models for the learned parts, connect them |
| **Backtesting** | Run through historical data, check every trade against expectations | Run through historical data, but ONLY on the held-out test set | Run through historical data, ensuring the model was never trained on the test period |
| **Validation** | Inspect individual trades. Do they match what you expected? Verify edge cases. | Out-of-sample metrics (Sharpe, drawdown, accuracy). Walk-forward analysis. | Both: inspect explicit logic trades AND validate model components out-of-sample |
| **Sensitivity analysis** | Change each parameter slightly. Does performance collapse? | Ablation study: remove features one at a time. Does performance change? | Both |
| **Paper trading** | Run forward in real-time without money. Compare signals to what you would have done manually. | Run forward and compare model predictions to actual outcomes. Monitor calibration. | Both |

---

## 7. Codification Patterns Catalog

This section catalogs specific, reusable patterns for common strategy operations. Each pattern shows both the white-box and black-box implementation.

### 7.1 Trend Detection

| Approach | Type | Implementation |
|---|---|---|
| **Moving average slope** | White-box | `trend = "up" if SMA(close, 20)[-1] > SMA(close, 20)[-5] else "down"` |
| **Higher highs / higher lows** | White-box | Compare last 2 swing highs and last 2 swing lows. Both higher = uptrend. |
| **ADX-based** | White-box | `trending = ADX(bars, 14)[-1] > 25` |
| **Linear regression slope** | White-box | Fit a linear regression to the last N closes. Slope > threshold = uptrend. |
| **HMM regime** | Black-box | Train HMM on returns. Classify current regime as trending or non-trending. |
| **Neural network classifier** | Black-box | Train on labeled "trending" vs "not trending" windows. |

### 7.2 Mean Reversion Detection

| Approach | Type | Implementation |
|---|---|---|
| **Bollinger Band deviation** | White-box | `overextended = close < BB_lower(close, 20, 2.0)` |
| **Z-score of spread** | White-box | For pairs: `zscore = (spread - mean(spread, 60)) / std(spread, 60)`. Overextended if abs(zscore) > 2. |
| **RSI extremes** | White-box | `oversold = RSI(close, 14) < 30` |
| **Cointegration model** | Hybrid | Test for cointegration (white-box), estimate hedge ratio with Kalman filter (model-learned), trade deviation (white-box rules). |
| **Autoencoder reconstruction error** | Black-box | Train autoencoder on "normal" price behavior. High reconstruction error = abnormal = potential reversion setup. |

### 7.3 Breakout Detection

| Approach | Type | Implementation |
|---|---|---|
| **Price exceeds N-bar high** | White-box | `breakout = close > max(high[-N:])` |
| **Range contraction → expansion** | White-box | `ATR(5) / ATR(20) < 0.6` (contraction). When `close > range_high`, breakout. |
| **Volume confirmation** | White-box | `breakout AND volume > 1.5 * avg_volume(20)` |
| **ML breakout quality scorer** | Hybrid | White-box detects breakout. ML model scores probability of follow-through based on context features. |

### 7.4 Support / Resistance Level Identification

| Approach | Type | Implementation |
|---|---|---|
| **Swing point clustering** | White-box | Find all swing highs/lows. Cluster those within X ATR of each other. The cluster midpoint is the level. |
| **Volume profile** | White-box | Compute volume at each price level over N bars. High-volume nodes are S/R levels. |
| **Round numbers** | White-box | Levels at whole numbers, half numbers, quarter numbers (for FX: 1.1000, 1.1050, etc.). |
| **ML level importance scoring** | Hybrid | White-box identifies candidate levels. ML model scores their importance based on how many times price reacted, how recently, and how strongly. |

### 7.5 Order Flow Analysis

| Approach | Type | Implementation |
|---|---|---|
| **Volume delta** | White-box | `delta = buy_volume - sell_volume` per bar. Cumulative delta divergence from price = signal. |
| **Absorption detection** | White-box | Large volume at a level without price movement = absorption. |
| **Order book imbalance** | White-box | `bid_depth / ask_depth > threshold` = buy pressure. |
| **Deep learning on order book** | Black-box | Feed level-2 order book snapshots to a CNN or LSTM. Predict short-term price direction. |

### 7.6 Risk Event Handling

| Approach | Type | Implementation |
|---|---|---|
| **Calendar-based news filter** | White-box | `if minutes_to_news_event < 30: no_new_trades()` |
| **Volatility spike detector** | White-box | `if ATR(5) > 2 * ATR(20): reduce_position_size(by=50%)` |
| **Drawdown circuit breaker** | White-box | `if daily_loss > 3% of equity: stop_trading_today()` |
| **Regime-aware dynamic risk** | Hybrid | HMM detects high-volatility regime → white-box rules reduce size and widen stops. |

---

## 8. Worked Examples: Manual Strategy to Code

### Example 1: "I buy pullbacks in an uptrend" → Three Codifications

**The manual strategy (what the discretionary trader does):**

> "I look at the daily chart. If the market is in an uptrend—making higher highs and higher lows—I wait for a pullback to the 21 EMA. When price touches the 21 EMA and forms a bullish engulfing candle, I buy. My stop goes below the pullback low. My target is 2× my risk. I don't trade this when the market is choppy or ranging."

#### White-Box Codification

```python
def detect_uptrend(bars, swing_lookback=5):
    """Explicit structural definition of an uptrend."""
    swing_highs = find_swing_highs(bars, lookback=swing_lookback)
    swing_lows = find_swing_lows(bars, lookback=swing_lookback)

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return False

    higher_high = swing_highs[-1].price > swing_highs[-2].price
    higher_low = swing_lows[-1].price > swing_lows[-2].price

    return higher_high and higher_low

def detect_pullback_to_ema(bars, ema_period=21):
    """Price has pulled back to touch the EMA."""
    ema = EMA(bars.close, ema_period)
    touched_ema = bars[-1].low <= ema[-1] <= bars[-1].high
    return touched_ema

def detect_bullish_engulfing(bars):
    """Explicit candlestick pattern definition."""
    prev = bars[-2]
    curr = bars[-1]

    prev_is_bearish = prev.close < prev.open
    curr_is_bullish = curr.close > curr.open
    curr_engulfs = curr.close > prev.open and curr.open < prev.close

    return prev_is_bearish and curr_is_bullish and curr_engulfs

def is_not_choppy(bars, adx_period=14, adx_threshold=20):
    """Explicit choppiness filter."""
    adx = ADX(bars, adx_period)
    return adx[-1] > adx_threshold

# Putting it all together
def generate_signal(bars):
    if not is_not_choppy(bars):
        return None
    if not detect_uptrend(bars):
        return None
    if not detect_pullback_to_ema(bars):
        return None
    if not detect_bullish_engulfing(bars):
        return None

    pullback_low = min(b.low for b in bars[-5:])  # Low of recent pullback
    entry_price = bars[-1].close
    stop_price = pullback_low - ATR(bars, 14)[-1] * 0.2  # Tiny buffer below pullback low
    risk = entry_price - stop_price
    target_price = entry_price + 2 * risk

    return Signal(
        direction="long",
        entry=entry_price,
        stop=stop_price,
        target=target_price,
        reason=f"Uptrend pullback to 21 EMA, bullish engulfing at {entry_price:.4f}"
    )
```

**Every decision is traceable. Every threshold is visible. Every trade can be explained.**

#### Black-Box Codification

```python
# Step 1: Define what we're predicting
# Target: will price be higher by at least 2*ATR in the next 10 bars
#         without first going lower by 1*ATR? (Binary: yes/no)

def compute_label(bars, entry_index, atr_value):
    """Did a hypothetical 2:1 RR trade from this bar succeed?"""
    entry = bars[entry_index].close
    stop = entry - 1 * atr_value
    target = entry + 2 * atr_value

    for i in range(entry_index + 1, min(entry_index + 20, len(bars))):
        if bars[i].low <= stop:
            return 0  # Stop hit first
        if bars[i].high >= target:
            return 1  # Target hit first
    return 0  # Ran out of time

# Step 2: Compute features for each bar (broad feature set)
def compute_features(bars, index):
    return {
        "return_1": bars[index].close / bars[index - 1].close - 1,
        "return_5": bars[index].close / bars[index - 5].close - 1,
        "return_20": bars[index].close / bars[index - 20].close - 1,
        "dist_to_ema21": (bars[index].close - EMA(bars.close[:index+1], 21)[-1]) / ATR(bars[:index+1], 14)[-1],
        "adx": ADX(bars[:index+1], 14)[-1],
        "rsi": RSI(bars[:index+1].close, 14)[-1],
        "vol_ratio": ATR(bars[:index+1], 5)[-1] / ATR(bars[:index+1], 20)[-1],
        "body_ratio": abs(bars[index].close - bars[index].open) / (bars[index].high - bars[index].low + 1e-10),
        "is_bullish": int(bars[index].close > bars[index].open),
        # ... 50+ more features
    }

# Step 3: Train a model
X, y = [], []
for i in range(100, len(train_bars) - 20):
    X.append(compute_features(train_bars, i))
    y.append(compute_label(train_bars, i, ATR(train_bars[:i+1], 14)[-1]))

model = LightGBM().fit(X, y, ...)

# Step 4: At runtime
def generate_signal(bars):
    features = compute_features(bars, -1)
    probability = model.predict_proba(features)[1]  # Probability of "1" (success)

    if probability > 0.62:  # Threshold tuned on validation data
        return Signal(direction="long", confidence=probability)
    return None
```

**You cannot explain why a specific trade was taken beyond "the model said 63%." But the model might capture patterns the explicit rules miss (e.g., it learned that the pullback strategy works better when the VIX term structure is in contango, even though the discretionary trader never consciously noticed that).**

#### Hybrid Codification

```python
def generate_signal(bars, ml_filter_model):
    # ── WHITE-BOX PART: structural requirements ──
    if not is_not_choppy(bars):
        return None
    if not detect_uptrend(bars):
        return None
    if not detect_pullback_to_ema(bars):
        return None
    if not detect_bullish_engulfing(bars):
        return None
    # At this point, the setup is structurally valid.

    # ── BLACK-BOX PART: quality filter ──
    context_features = compute_context_features(bars)
    # These features capture things the white-box rules DON'T check:
    # recent volatility regime, volume patterns, correlation with
    # broader market, time of day/week/month, etc.
    quality_score = ml_filter_model.predict_proba(context_features)[1]

    if quality_score < 0.55:
        return None  # Setup is valid but context is poor

    # ── WHITE-BOX PART: execution ──
    pullback_low = min(b.low for b in bars[-5:])
    entry_price = bars[-1].close
    stop_price = pullback_low - ATR(bars, 14)[-1] * 0.2
    risk = entry_price - stop_price
    target_price = entry_price + 2 * risk

    return Signal(
        direction="long",
        entry=entry_price,
        stop=stop_price,
        target=target_price,
        reason=f"WB: uptrend pullback engulfing. BB filter: quality={quality_score:.2f}"
    )
```

**The hybrid version takes only the white-box trades that the ML model thinks have the highest chance of success. It's more selective than pure white-box but more explainable than pure black-box.**

### Example 2: "Pairs Mean Reversion" → Three Codifications

**The manual strategy:**

> "I watch Coca-Cola (KO) and Pepsi (PEP). They normally move together. When one drops significantly relative to the other for no fundamental reason, I buy the laggard and short the leader. I exit when they converge."

#### White-Box Codification

```python
class PairsMeanReversionWB:
    def __init__(self):
        self.lookback = 60  # Days for z-score calculation
        self.entry_zscore = 2.0
        self.exit_zscore = 0.5
        self.stop_zscore = 3.5
        self.hedge_ratio = 1.0  # Fixed 1:1 dollar-neutral (simplistic)

    def compute_spread(self, ko_prices, pep_prices):
        return np.log(ko_prices) - self.hedge_ratio * np.log(pep_prices)

    def generate_signal(self, ko_bars, pep_bars):
        spread = self.compute_spread(ko_bars.close, pep_bars.close)
        mean = np.mean(spread[-self.lookback:])
        std = np.std(spread[-self.lookback:])
        zscore = (spread[-1] - mean) / std

        if zscore > self.entry_zscore:
            return Signal("short_KO_long_PEP", zscore=zscore)
        elif zscore < -self.entry_zscore:
            return Signal("long_KO_short_PEP", zscore=zscore)
        return None
```

**Fixed hedge ratio, fixed lookback, fixed thresholds. Fully inspectable.**

#### Black-Box Codification

```python
class PairsMeanReversionBB:
    def __init__(self, kalman_filter, lstm_model):
        self.kalman = kalman_filter  # Dynamically estimates hedge ratio
        self.lstm = lstm_model  # Predicts spread direction from sequence data

    def generate_signal(self, ko_bars, pep_bars, market_features):
        # Kalman filter dynamically estimates the time-varying hedge ratio
        hedge_ratio = self.kalman.update(ko_bars.close[-1], pep_bars.close[-1])
        spread = np.log(ko_bars.close[-1]) - hedge_ratio * np.log(pep_bars.close[-1])

        # LSTM predicts: will the spread revert in the next 5 days?
        spread_sequence = self.compute_spread_sequence(ko_bars, pep_bars, hedge_ratios)
        features = np.column_stack([spread_sequence, market_features])
        reversion_prob = self.lstm.predict(features)

        if reversion_prob > 0.65 and spread > some_threshold:
            return Signal("short_KO_long_PEP", confidence=reversion_prob)
        return None
```

**Hedge ratio is learned (Kalman filter). Reversion prediction is a neural network. You know the general concept but not the specific decision logic for any given trade.**

#### Hybrid Codification

```python
class PairsMeanReversionHybrid:
    def __init__(self, kalman_filter):
        self.kalman = kalman_filter  # BB: dynamic hedge ratio
        # WB: all thresholds and rules are explicit
        self.entry_zscore = 2.0
        self.exit_zscore = 0.5
        self.stop_zscore = 3.5
        self.lookback = 60

    def generate_signal(self, ko_bars, pep_bars):
        # BB component: dynamic hedge ratio
        hedge_ratio = self.kalman.update(ko_bars.close[-1], pep_bars.close[-1])

        # WB component: explicit spread calculation and z-score
        spread = np.log(ko_bars.close) - hedge_ratio * np.log(pep_bars.close)
        mean = np.mean(spread[-self.lookback:])
        std = np.std(spread[-self.lookback:])
        zscore = (spread[-1] - mean) / std

        # WB component: explicit entry/exit rules
        if abs(zscore) > self.entry_zscore:
            direction = "short_KO_long_PEP" if zscore > 0 else "long_KO_short_PEP"
            return Signal(direction, zscore=zscore, hedge_ratio=hedge_ratio)
        return None
```

**The hedge ratio adapts statistically (black-box), but all trading rules are explicit (white-box).**

---

## 9. Component and Building Block Reference

### 9.1 Indicators (White-Box Building Blocks)

| Indicator | Purpose in Strategy | Parameters | Typical Use |
|---|---|---|---|
| **SMA** | Trend direction, support/resistance | Period | Trend filter, baseline |
| **EMA** | Same as SMA, more responsive | Period | Faster trend detection |
| **RSI** | Momentum, overbought/oversold | Period (default 14) | Mean reversion entry, momentum filter |
| **MACD** | Trend direction and momentum | Fast, slow, signal periods | Trend confirmation, divergence |
| **ATR** | Volatility measure | Period (default 14) | Stop placement, position sizing, regime classification |
| **ADX** | Trend strength (not direction) | Period (default 14) | Regime filter (trending vs ranging) |
| **Bollinger Bands** | Volatility envelope around mean | Period, std multiplier | Mean reversion entry, breakout detection |
| **VWAP** | Volume-weighted average price | Anchor (session, day) | Institutional bias, entry zones |
| **Volume Profile** | Volume distribution by price | Lookback, resolution | Support/resistance, value area |
| **Stochastic** | Momentum oscillator | K, D, smoothing | Mean reversion, divergence |
| **Ichimoku** | Multi-purpose trend system | Tenkan, Kijun, Senkou, Chikou | Trend direction, support/resistance, entry signals |

### 9.2 Models (Black-Box Building Blocks)

| Model | Type | Inputs | Outputs | Training Requirement |
|---|---|---|---|---|
| **LightGBM / XGBoost** | Supervised, tabular | Feature vector (one row per bar) | Probability or regression value | Thousands of labeled examples |
| **Random Forest** | Supervised, tabular | Feature vector | Probability or regression value | Hundreds to thousands of examples |
| **LSTM** | Supervised, sequential | Sequence of feature vectors | Prediction for next step | Thousands of sequences |
| **Transformer** | Supervised, sequential | Sequence of feature vectors | Prediction (can attend to any position) | Large datasets (tens of thousands+) |
| **HMM** | Unsupervised / regime | Sequence of observations | Hidden state probabilities | Moderate (hundreds of data points per regime) |
| **Kalman Filter** | Online estimation | Sequential observations | Filtered state estimate | Minimal (learns online) |
| **Reinforcement Learning** | Policy learning | State (features + position) | Action (buy/sell/hold/size) | Millions of simulated steps |
| **BERT / FinBERT** | NLP classifier | Text (news, filings) | Sentiment score | Pre-trained + fine-tuning on domain data |
| **Autoencoder** | Anomaly detection | Feature vector or sequence | Reconstruction error | Thousands of "normal" examples |

### 9.3 Data Sources

| Data Type | What It Provides | Required For |
|---|---|---|
| **OHLCV** | Price and volume bars | Every strategy |
| **Tick data** | Individual trades with timestamps | Order flow analysis, microstructure features |
| **Level 2 / Order book** | Bid and ask depth at multiple price levels | Order flow, institutional activity detection |
| **Economic calendar** | Scheduled macro events (NFP, CPI, FOMC, etc.) | News filters, event-driven strategies |
| **Macro data** | GDP, inflation, employment, yields, etc. | Macro regime classification, fundamental strategies |
| **Corporate fundamentals** | Earnings, revenue, P/E, debt ratios, etc. | Fundamental equity strategies |
| **News / text** | Headlines, articles, transcripts, filings | NLP-driven sentiment strategies |
| **Alternative data** | Satellite imagery, credit card data, web traffic, etc. | Unique alpha in institutional quant strategies |
| **Cross-asset data** | Prices of related instruments, indices, sectors | Correlation features, relative value, regime context |

---

## 10. Decision Framework: Choosing Your Approach

### 10.1 The Decision Matrix

| Factor | Favors White-Box | Favors Black-Box | Favors Hybrid |
|---|---|---|---|
| **You can explain the edge** | ✓ | | |
| **The edge is "I know it when I see it"** | | ✓ | |
| **You need to trust the strategy with real money quickly** | ✓ | | ✓ |
| **You have >10 years of clean data** | | ✓ | ✓ |
| **You have <2 years of data** | ✓ | | |
| **The strategy trades 5+ times per day** | | ✓ | ✓ |
| **The strategy trades 2-3 times per week** | ✓ | | ✓ |
| **You need to understand every loss** | ✓ | | |
| **You only care about aggregate Sharpe** | | ✓ | |
| **The edge is regime-dependent** | | | ✓ |
| **You're combining multiple ideas** | | | ✓ |
| **You need to satisfy regulators or investors** | ✓ | | ✓ |
| **You're a solo trader/small team** | ✓ | | ✓ |
| **You have ML infrastructure (training, serving, monitoring)** | | ✓ | ✓ |
| **You don't have ML infrastructure** | ✓ | | |
| **The market you trade is highly efficient (FX majors, ES)** | | ✓ | ✓ |
| **The market has clear structural features (crypto, small caps)** | ✓ | | ✓ |

### 10.2 Starting Recommendation

**If you're unsure, start white-box and add hybrid components incrementally.**

1. **Day 1:** Write the strategy as full white-box. Every rule explicit. Every parameter hard-coded.
2. **After backtesting:** If performance is sensitive to specific parameter values, introduce systematic optimization (→ Hybrid Pattern 1).
3. **After live testing:** If the strategy generates too many low-quality setups, train a quality filter (→ Hybrid Pattern 2).
4. **After studying failure modes:** If the strategy fails during certain market conditions but thrives in others, add regime classification (→ Hybrid Pattern 3).
5. **After reaching the limits of explicit rules:** If you've exhausted what you can specify manually but believe there's more edge in the data, explore full black-box models.

---

## 11. Failure Modes and How to Avoid Them

### 11.1 White-Box Failure Modes

| Failure Mode | What It Looks Like | How to Avoid It |
|---|---|---|
| **Over-specification** | Too many conditions. The strategy rarely triggers. When it does, it works beautifully—but there are only 12 trades in 5 years. Not enough to be statistically meaningful. | After writing all rules, count the trade frequency. If <30 trades per year, consider relaxing conditions. |
| **Curve-fitting the narrative** | The rules perfectly describe *past* market behavior but don't generalize. You wrote rules that match what you've seen, not what generates an edge. | Walk-forward test. If the strategy works in-sample but fails out-of-sample, you've fit the narrative, not the edge. |
| **Rigidity** | The rules work in one regime but fail catastrophically in another. No adaptation mechanism. | Add regime awareness (even white-box regime classification helps). Or add circuit breakers that halt trading when conditions change. |
| **Indicator redundancy** | Using 5 indicators that all measure the same thing (momentum). You think you have 5 independent confirmations, but you really have 1 signal measured 5 ways. | Check indicator correlations. Ensure each indicator captures a *different* dimension of the market. |
| **Ambiguous discretion buried in code** | Rules that seem explicit but have hidden ambiguity: "find the most important support level." What does "most important" mean computationally? | Review every function. If it contains a word that requires human judgment (important, strong, significant, clear, obvious), it's not fully codified. Replace it with a computable definition. |

### 11.2 Black-Box Failure Modes

| Failure Mode | What It Looks Like | How to Avoid It |
|---|---|---|
| **Overfitting** | 90% accuracy in-sample, 50% out-of-sample. The model memorized the training data instead of learning generalizable patterns. | Walk-forward validation. Regularization. Feature selection. Simpler models as baselines. |
| **Data leakage** | Model has unrealistically high accuracy because future information leaked into the features. | Audit every feature computation: does it use any data from after the prediction point? Use strict temporal splits. Add purge and embargo periods. |
| **Survivorship bias** | Training data only includes assets that still exist today. Assets that went bankrupt or delisted are missing. The model learns from a biased sample. | Use survivorship-bias-free datasets. Include delisted securities in the training data. |
| **Concept drift** | Model worked well for 2 years, then gradually degraded because the market regime changed and the patterns it learned no longer apply. | Monitor model performance in real-time. Retrain on schedule. Implement drift detection. |
| **Adversarial degradation** | If many participants use similar models, the patterns they exploit get arbitraged away. The model's own success (at scale) destroys its edge. | Monitor decay rate. Diversify across many uncorrelated signals. |
| **Lack of economic sense** | Model learns spurious correlations (e.g., "when the temperature in Oslo is 23°C, buy Tesla"). Works on training data, meaningless in reality. | Feature audit by domain experts. Sanity checks on feature importance. Remove features that have no plausible causal or structural relationship to the target. |

### 11.3 Hybrid Failure Modes

| Failure Mode | What It Looks Like | How to Avoid It |
|---|---|---|
| **Boundary confusion** | Unclear which component (white-box or black-box) is responsible for what. When the strategy fails, you don't know which part to fix. | Document the boundary explicitly. Tag every decision as "WB" or "BB." Log which component drove each trade. |
| **Over-filtering** | The ML filter rejects almost everything the white-box generates. The strategy barely trades. The ML filter may be overly conservative or learning from noise. | Track the filter rejection rate. If >80% of white-box setups are rejected, examine why. The filter might be overfitting to noise in the validation data. |
| **Mismatched optimization** | The white-box parameters were optimized independently of the ML model. The ML model was trained independently of the white-box rules. But they interact. | Optimize the full pipeline end-to-end when possible. At minimum, validate the full system (WB + BB together) on held-out data, not just the components separately. |

---

## 12. Glossary

| Term | Definition |
|---|---|
| **ATR (Average True Range)** | A measure of price volatility. The average of the "true range" (which accounts for gaps) over N bars. |
| **Backtest** | Running a strategy on historical data to see how it would have performed. |
| **Calibration** | The degree to which a model's confidence scores match reality. If the model says "70% probability" on 100 trades, about 70 should be winners. |
| **Circuit Breaker** | A hard-coded rule that stops the strategy from trading when conditions are dangerous (e.g., max daily loss reached). |
| **Concept Drift** | When the statistical relationship between features and target changes over time, causing a trained model to degrade. |
| **Cointegration** | A statistical property where two non-stationary time series have a stationary linear combination. Used in pairs trading. |
| **Data Leakage** | When information from outside the training dataset (often future information) is used to create the model. Produces unrealistically good results that won't replicate in live trading. |
| **Edge** | The statistical advantage that makes a strategy profitable after costs. |
| **Ensemble** | A model composed of many simpler models whose predictions are combined (averaged, voted, etc.). |
| **Feature** | A computed input variable fed to a model. E.g., "10-day return," "RSI value," "volume ratio." |
| **Feature Store** | A centralized repository of pre-computed features, versioned and timestamped, used to ensure consistency between training and inference. |
| **FVG (Fair Value Gap)** | A three-candle price pattern where the wicks of the outer candles don't overlap, leaving a "gap" in traded prices. Used in ICT/SMC methodology. |
| **HMM (Hidden Markov Model)** | A statistical model where the system is assumed to be in one of several hidden states, transitioning between them with certain probabilities, and emitting observable data according to each state's distribution. |
| **Kalman Filter** | A recursive algorithm that estimates the state of a dynamic system from noisy observations. Used for dynamic hedge ratio estimation and signal filtering. |
| **LSTM (Long Short-Term Memory)** | A type of recurrent neural network designed to learn from sequential data by maintaining a cell state that can remember or forget information over long sequences. |
| **MDP (Markov Decision Process)** | A mathematical framework for modeling decision-making where outcomes are partly random and partly controlled by a decision-maker. Foundation for reinforcement learning. |
| **Market Impact** | The adverse price movement caused by your own order. Large orders push the price against you. |
| **Order Block** | The last opposing candle (or group of candles) before an impulsive price move. Used in ICT/SMC methodology as a potential entry zone. |
| **Overfitting** | When a model (or a set of rules) is too closely adapted to historical data, capturing noise rather than signal, and fails on new data. |
| **Purging** | Removing training data points that are close in time to test data points, to prevent label leakage in time-series cross-validation. |
| **R-Multiple** | The profit or loss of a trade expressed as a multiple of the initial risk. A 2R trade made twice the amount risked. |
| **Regime** | A distinct market state characterized by specific statistical properties (e.g., trending/ranging, high/low volatility). |
| **Reinforcement Learning** | A type of machine learning where an agent learns to take actions in an environment to maximize cumulative reward through trial and error. |
| **Sharpe Ratio** | Risk-adjusted return: (mean return - risk-free rate) / standard deviation of returns. Higher is better. |
| **State Machine** | A computational model consisting of a finite set of states, transitions between them, and actions triggered by transitions. |
| **Survivorship Bias** | The error of only analyzing assets that currently exist, ignoring those that were delisted or went bankrupt, which biases results upward. |
| **Transformer** | A neural network architecture based on self-attention mechanisms, capable of processing entire sequences in parallel and learning which parts of the sequence are most relevant to each other. |
| **Walk-Forward Optimization** | An optimization method where parameters are optimized on a rolling window of data and tested on the subsequent period, simulating real-time strategy deployment. |
| **Z-Score** | The number of standard deviations a value is from the mean. Used to normalize values and detect extremes. |

---

*This document is a living reference. As new codification patterns, models, or strategy types are encountered, they should be added to the appropriate section.*