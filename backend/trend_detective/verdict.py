"""The verdict: plain-English wording built by fixed rules from TrendStats.

Deterministic and free of any AI. Rules: docs/API_CONTRACT.md, "Rules behind the numbers".
No sentence states a number or a direction that was not computed.
"""

from __future__ import annotations

from trend_detective.models import (
    AUTOCORRELATION_THRESHOLD,
    MIN_YEARS_FOR_TREND,
    Direction,
    Evidence,
    Location,
    Period,
    Season,
    TrendStats,
    Variable,
    Verdict,
)
from trend_detective.wording import (
    format_number,
    format_p,
    lowercase_first,
    period_text,
    place_name,
    plural,
    with_unit,
)

SHORT_RECORD_YEARS = 20
METHODS_DISAGREE_CAVEAT = (
    "The t-test and the Mann-Kendall test disagree, so treat the result with caution."
)
MOTION: dict[Direction, str] = {"up": "rising", "down": "falling", "flat": "changing"}


def _headline(name: str, evidence: Evidence, direction: Direction) -> str:
    lower = lowercase_first(name)
    if evidence == "strong":
        return f"Case closed: {lower} is {MOTION[direction]}."
    if evidence == "mixed":
        return f"Inconclusive: the evidence on {lower} is mixed."
    if evidence == "none":
        return f"No significant trend found in {lower}."
    return f"Not enough data to judge {lower}."


def _what(name: str, evidence: Evidence, direction: Direction) -> str:
    if evidence == "strong":
        return f"{name} is {MOTION[direction]}."
    if evidence == "mixed":
        if direction == "flat":
            return f"{name} shows mixed signals."
        return f"{name} may be {MOTION[direction]}, but only one of the two tests is convinced."
    if evidence == "none":
        return f"{name} shows no significant rise or fall."
    return f"{name} could not be tested for a trend."


def _how_much(trend: TrendStats | None) -> str:
    if trend is None:
        return "No slope was computed."
    slope = with_unit(format_number(trend.sen.slope_per_decade, signed=True), trend.unit)
    change = with_unit(format_number(trend.total_change, signed=True), trend.unit)
    percent = "" if trend.percent_change is None else f" ({trend.percent_change:+.0f}%)"
    text = f"{slope} per decade (Sen's slope); "
    text += f"the fitted line changes by {change} over the whole period{percent}."
    if trend.evidence in ("none", "mixed"):
        text += " This change is not statistically established."
    return text


def _p_values(trend: TrendStats) -> str:
    ols = format_p(trend.ols.p_value)
    if trend.autocorrelation_corrected and trend.mann_kendall.p_value_hamed_rao is not None:
        mk = format_p(trend.mann_kendall.p_value_hamed_rao)
        return f"t-test {ols}, Mann-Kendall corrected for autocorrelation {mk}"
    return f"t-test {ols}, Mann-Kendall {format_p(trend.mann_kendall.p_value)}"


def _how_sure(trend: TrendStats | None, n_valid: int) -> str:
    if trend is None:
        return _insufficient_reason(n_valid)
    if trend.evidence == "strong":
        return f"Both tests agree this is very unlikely to be chance ({_p_values(trend)})."
    if trend.evidence == "mixed":
        return (
            f"Only one of the two tests finds a significant trend ({_p_values(trend)}), "
            "so it is uncertain."
        )
    return (
        "Neither test finds a change that stands out from the ordinary ups and downs "
        f"between years: it could be chance ({_p_values(trend)})."
    )


def _insufficient_reason(n_valid: int) -> str:
    if n_valid >= MIN_YEARS_FOR_TREND:
        return "The series has the same value in every year, so there is no trend to test."
    needed = f"A trend test needs at least {MIN_YEARS_FOR_TREND} years with data"
    if n_valid > 0:
        return f"{needed}, and this record has {n_valid}."
    return f"{needed}."


def _autocorrelation_caveat(trend: TrendStats) -> str | None:
    lag1 = trend.lag1_autocorrelation
    if abs(lag1) <= AUTOCORRELATION_THRESHOLD:
        return None
    if trend.autocorrelation_corrected:
        return (
            f"Consecutive years are {'alike' if lag1 > 0 else 'alternating'} "
            f"(autocorrelation {lag1:+.2f}), so the Mann-Kendall p-value was corrected for it "
            "(Hamed and Rao method). The t-test p-value was not corrected and may be too small."
        )
    if lag1 > 0:
        return (
            f"Consecutive years are alike (autocorrelation {lag1:+.2f}), which makes the tests "
            "over-confident: the true p-values are probably larger than shown."
        )
    return (
        f"Consecutive years tend to alternate (autocorrelation {lag1:+.2f}), but the tests assume "
        "independent years, so their p-values are only approximate."
    )


def _caveats(trend: TrendStats | None) -> list[str]:
    if trend is None:
        return []
    found = [
        _autocorrelation_caveat(trend),
        _missing_caveat(trend),
        None if trend.methods_agree else METHODS_DISAGREE_CAVEAT,
        _short_caveat(trend),
    ]
    return [c for c in found if c is not None]


def _missing_caveat(trend: TrendStats) -> str | None:
    if trend.n_missing == 0:
        return None
    verb = "has" if trend.n_missing == 1 else "have"
    return (
        f"{plural(trend.n_missing, 'year')} {verb} no data and "
        f"{'was' if trend.n_missing == 1 else 'were'} left out ({trend.n} years used)."
    )


def _short_caveat(trend: TrendStats) -> str | None:
    if trend.n >= SHORT_RECORD_YEARS:
        return None
    return (
        f"Short record ({trend.n} years): over so few years, natural cycles can look like a trend."
    )


def build_verdict(
    variable: Variable,
    location: Location,
    period: Period,
    season: Season,
    trend: TrendStats | None,
    *,
    n_valid: int = 0,
) -> Verdict:
    """The verdict for one variable at one place. `trend` is None when it could not be computed;
    `n_valid` (years with data) then explains why."""
    evidence: Evidence = "insufficient" if trend is None else trend.evidence
    direction: Direction = "flat" if trend is None else trend.direction
    return Verdict(
        evidence=evidence,
        headline=_headline(variable.name, evidence, direction),
        what=_what(variable.name, evidence, direction),
        where=f"{place_name(location)}, {period_text(period, season)}.",
        how_much=_how_much(trend),
        how_sure=_how_sure(trend, n_valid),
        caveats=_caveats(trend),
    )
