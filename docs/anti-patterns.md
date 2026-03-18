# Anti-Pattern Catalog

Six failure modes discovered in production, each with a programmatic guard to prevent recurrence. These were all found the hard way — production incidents, silent failures, or user-reported bugs that tests should have caught but didn't.

---

## 1. Silent Defaults

**Discovery:** A function that was supposed to return 30 days of trade history was silently returning only today's data when called without explicit date parameters. Dashboards looked fine (today's data rendered correctly) but all historical analysis was wrong.

**Root cause:** Optional parameters with sensible-sounding defaults that narrow the query scope without the caller realizing it.

**Guard:**
```python
# Bad: silent default masks data scope
def get_trades(start_date=None):
    if start_date is None:
        start_date = datetime.now().date()  # silently returns only today

# Good: explicit is required
def get_trades(start_date: date, end_date: date):
    ...  # caller must think about the date range
```

**Rule:** All date-range functions require explicit start and end parameters. No implicit "default to today" behavior in any data retrieval path.

---

## 2. Stubs That Never Execute

**Discovery:** A learning pipeline was fully coded — data loading, pattern extraction, persistence — but three chained bugs prevented it from ever executing. All unit tests passed because they tested individual functions in isolation. The integration path was never exercised.

**Root cause:** Testing individual components without testing the full execution path. Combined with debug-level logging that made the silent failure invisible.

**Guard:**
```python
# Integration test that verifies the full pipeline runs end-to-end
def test_learning_pipeline_executes():
    result = run_learning_pipeline(test_data)
    assert result.patterns_extracted > 0  # not just "didn't crash"
    assert result.file_written is True     # verify the output exists
```

**Rule:** Every pipeline has an integration test that verifies actual execution and output, not just that individual functions return expected values.

---

## 3. Data Staleness

**Discovery:** A tracking file stopped being updated when the upstream cron job failed. The system continued trading using stale data for 3 days before anyone noticed. Stale weather observations led to trades based on outdated conditions.

**Root cause:** No freshness monitoring on data files. The system assumed that if a file existed, its data was current.

**Guard:**
```python
def check_freshness(filepath, max_age_minutes=30):
    """Raise if file is older than max_age_minutes."""
    mtime = os.path.getmtime(filepath)
    age = time.time() - mtime
    if age > max_age_minutes * 60:
        raise StaleDataError(
            f"{filepath} is {age/60:.0f}min old (max: {max_age_minutes}min)"
        )
```

**Rule:** Every tracking file has a Doctor freshness check with a configurable staleness threshold. The healer cycle verifies freshness 7 times per day during market hours.

---

## 4. String Matching Without Normalization

**Discovery:** A player named "Nikola Jokić" in one data source appeared as "Nikola Jokic" in another. A player listed as "Marcus Morris Jr." in one source was "Marcus Morris" in another. Simple `.lower()` comparison missed both cases, causing duplicate entries and missed correlations.

**Root cause:** Multiple data sources use different conventions for names, suffixes, and Unicode characters.

**Guard:**
```python
def normalize_player_name(name: str) -> str:
    """Canonical form for cross-source matching."""
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode()  # ć → c
    name = re.sub(r"\b(Jr|Sr|II|III|IV)\.?\b", "", name)
    name = re.sub(r"\s+", " ", name).strip().lower()
    return name
```

**Rule:** All name comparisons route through the normalization utility. Raw `.lower()` for player/entity name comparison is flagged in code review.

---

## 5. Silent Exception Swallowing

**Discovery:** The IC (Investment Committee) learnings pipeline was fully coded but 3 chained bugs prevented it from ever executing. The exceptions were caught and logged at `debug` level. Since production runs at `info` level, the failures were completely invisible. The pipeline appeared healthy in all monitoring.

**Root cause:** `except Exception as e: log.debug(f"IC error: {e}")` — catching broad exceptions and logging them below the production log threshold.

**Guard:**
```python
# Bad: invisible in production
except Exception as e:
    log.debug(f"Failed: {e}")  # nobody sees this

# Good: visible and actionable
except Exception as e:
    log.warning(f"IC pipeline failed: {e}", exc_info=True)
    # or better: raise, and let the healer handle it
```

**Rule:** Minimum `warning` level for caught exceptions in production pipelines. `debug`-level exception logging is flagged in code review. If an exception is worth catching, it is worth someone seeing.

---

## 6. Phantom Data

**Discovery:** A player with `season_avg=0` (data source had no stats for them) still received an A+ confidence grade because the grading system treated 0 as a valid value and calculated a grade based on the delta from the prop line. The system generated high-confidence picks on players it had no real data for.

**Root cause:** No distinction between "the value is zero" and "the value is missing." The grading function operated on whatever number it received.

**Guard:**
```python
def validate_player_data(player: dict) -> bool:
    """Reject picks when critical data is missing."""
    required = ["season_avg", "last_5_avg", "games_played"]
    for field in required:
        value = player.get(field)
        if value is None or value == 0:
            log.warning(f"Missing {field} for {player['name']}, rejecting pick")
            return False
    if player["games_played"] < 5:
        log.warning(f"Insufficient sample for {player['name']}, rejecting pick")
        return False
    return True
```

**Rule:** Critical data fields are validated before grade calculation. Missing or zero-value data results in pick rejection, not default-value substitution. The system must explicitly distinguish between "measured zero" and "not measured."

---

## Meta-Pattern: Why These Keep Happening

All six anti-patterns share a common structure:

1. **The happy path works.** Unit tests pass. The dashboard looks fine.
2. **The failure mode is silent.** No errors, no crashes, no alerts.
3. **The data looks plausible.** Stale data still looks like data. Zero still looks like a number. An empty function still returns successfully.

The fix is always the same: **make the failure loud.** Validate inputs. Check freshness. Test the full path, not just the components. Log at a level that someone will actually see.

---

*Each anti-pattern is named, documented, and guarded. Unnamed failures repeat.*
