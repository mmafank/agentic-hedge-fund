# Quantitative Metrics Suite

27 modules, 7,300+ lines of mathematical and statistical tooling. Every module is integrated into live strategy operations — these are not CLI-only analysis tools.

---

## Architecture

```
metrics/
├── garch.py              # GARCH(1,1) volatility modeling
├── var.py                # Value at Risk (historical + parametric)
├── monte_carlo_kelly.py  # Kelly criterion with Monte Carlo simulation
├── black_scholes.py      # Options pricing (European)
├── frank_wolfe.py        # Portfolio optimization (Python adapter)
├── frank_wolfe_rust/     # Frank-Wolfe solver (Rust, compiled to .so)
├── cointegration.py      # ADF stationarity + Engle-Granger
├── conformal.py          # Conformal prediction intervals
├── jump_diffusion.py     # Merton jump-diffusion model
├── lmsr.py               # Logarithmic Market Scoring Rule
├── options_greeks.py     # Delta, gamma, theta, vega, rho
├── edge_decay.py         # Rolling win-rate degradation monitor
├── sharpe.py             # Sharpe ratio (annualized)
├── brier.py              # Brier score for probability calibration
├── significance.py       # Binomial test, z-test, chi-squared
├── atr.py                # Average True Range
├── alpha_decomp.py       # Alpha decomposition
├── correlation.py        # Cross-asset correlation matrix
├── drawdown.py           # Maximum drawdown calculation
├── entropy.py            # Shannon entropy for signal diversity
├── hurst.py              # Hurst exponent (mean reversion vs trend)
├── information_ratio.py  # Information ratio vs benchmark
├── kurtosis_skew.py      # Distribution shape analysis
├── regime.py             # Market regime detection
├── sortino.py            # Sortino ratio (downside deviation only)
├── tail_risk.py          # Conditional VaR (Expected Shortfall)
└── treynor.py            # Treynor ratio (systematic risk adjustment)
```

---

## Live Integrations

| Module | Strategy | How It Is Used |
|--------|----------|---------------|
| GARCH | BTC Signal | Dynamic position sizing based on current volatility regime |
| VaR | BTC + SOL | Risk guardrail — refuses trades that exceed daily VaR threshold |
| Monte Carlo Kelly | BTC + SOL | Sizing cap via simulated Kelly criterion (prevents over-betting) |
| Black-Scholes | Lottery Ticket | Options enrichment — theoretical value vs market price |
| Frank-Wolfe | Lottery Ticket | Portfolio allocation across candidate positions |
| Cointegration | Combo Arb | ADF test validates pair stationarity before entry |
| Conformal | Weather | Distribution-free prediction intervals for observation forecasts |
| Edge Decay | All strategies | Rolling 30-day WR vs all-time, flags >10pp degradation |
| Sharpe | Doctor | Health metric for strategy performance assessment |
| Brier | Weather + CPI | Calibration accuracy of probability forecasts |
| Significance | All strategies | Validates that win rates are statistically significant (not luck) |

---

## Design Principles

### No Black Boxes
Every module exposes its intermediate calculations, not just final results. When the GARCH model produces a volatility estimate, you can inspect the conditional variance series, the fitted parameters, and the log-likelihood. This is critical for debugging at 4 AM when a trade looks wrong.

### Chronological Splits Only
ML pipelines (XGBoost calibrators) use strict chronological train/test splits. No random shuffling. No future data leakage. The test set is always the most recent data, simulating real trading conditions.

```python
# Correct: chronological split
train = data[data.date < split_date]
test = data[data.date >= split_date]

# Wrong: random split (leaks future information)
train, test = train_test_split(data, test_size=0.2, random_state=42)
```

### JSON Serialization Only
Trained models are saved in XGBoost's native JSON format. No pickle files. Pickle allows arbitrary code execution during deserialization — an unacceptable risk for a system that handles financial decisions.

```python
# Safe: JSON serialization
model.save_model("model.json")
loaded = xgb.Booster()
loaded.load_model("model.json")

# Unsafe: pickle serialization
# pickle.dump(model, open("model.pkl", "wb"))  # NEVER
```

### Defensive Numerics
All calculations handle edge cases:
- Division by zero → return 0 or NaN with warning, never crash
- Empty arrays → explicit check before any statistical operation
- NaN propagation → detected and logged, not silently passed through

---

## The Frank-Wolfe Implementation

The portfolio optimizer has three implementations:

1. **Rust solver** (`frank_wolfe_rust/`) — Compiled to a shared library (`.so`), called from Python via ctypes. Handles the hot loop of the Frank-Wolfe conditional gradient algorithm.
2. **Python adapter** (`frank_wolfe.py`) — Wraps the Rust solver with input validation, constraint checking, and result formatting.
3. **Legacy Python** — Pure Python fallback for environments where the Rust binary is not available.

**Why Rust for this one module?** The Frank-Wolfe algorithm requires many iterations over a large constraint set. Python is too slow for real-time use. Rust gives 50-100x speedup for the inner loop while keeping the rest of the codebase in Python.

---

## Testing

95+ tests across the suite. Each module has:
- **Unit tests** for mathematical correctness (known inputs → known outputs)
- **Edge case tests** (empty data, single data point, all-same values)
- **Integration tests** verifying the module works within the live strategy pipeline

```python
def test_sharpe_ratio_known_values():
    """Verify against textbook calculation."""
    returns = pd.Series([0.01, 0.02, -0.005, 0.015, 0.008])
    expected = 2.83  # pre-calculated
    assert abs(sharpe_ratio(returns) - expected) < 0.1

def test_sharpe_ratio_empty():
    """Empty returns should not crash."""
    assert sharpe_ratio(pd.Series([])) == 0.0

def test_var_exceeds_position():
    """VaR should block trades exceeding risk threshold."""
    var_95 = calculate_var(returns, confidence=0.95)
    assert not should_trade(position_size=1000, var=var_95, max_var=50)
```

---

*Every module earns its place by being wired into a live strategy. Analysis tools that are only used from the CLI get deprioritized. If it does not affect a trade decision, it does not need to exist.*
