from django import template

from portal.services import match_tier as _match_tier

register = template.Library()


@register.filter
def currency_k(value):
    if value is None:
        return "—"
    return f"${round(value / 1000)}k"


@register.filter
def to_k(value):
    """Plain integer thousands — for data-* attributes jobs.js compares numerically."""
    if value is None:
        return 0
    return round(value / 1000)


@register.filter
def match_label(pct):
    return _match_tier(pct)[0]


@register.filter
def match_variant(pct):
    return _match_tier(pct)[1]


@register.filter
def initials(name):
    if not name:
        return "?"
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


@register.filter
def pipe_join(items, sep="|"):
    return sep.join(str(i) for i in items)


@register.filter
def score_ring_variant(score):
    return "success" if score is not None and score >= 85 else "info"


@register.filter
def score_fill_variant(score):
    """Matches candidates.html's ra-score__fill modifiers: plain for the
    very top band, success for strong, danger for weak."""
    if score is None:
        return ""
    if score >= 90:
        return ""
    if score >= 70:
        return "success"
    return "danger"


_STAGE_VARIANTS = {
    "new_applied": "neutral",
    "screening": "neutral",
    "review": "info",
    "technical_test": "warning",
    "interview": "warning",
    "shortlisted": "info",
    "offer": "info",
    "hired": "success",
    "rejected": "danger",
}


@register.filter
def stage_variant(stage):
    return _STAGE_VARIANTS.get(stage, "neutral")


@register.filter
def experience_range(exp):
    from datetime import date

    end_label = exp.end_date.strftime("%b %Y") if exp.end_date else "Present"
    end_for_calc = exp.end_date or date.today()
    years = (end_for_calc - exp.start_date).days / 365.25
    return f"{exp.start_date.strftime('%b %Y')} – {end_label} ({years:.1f} yrs)"
