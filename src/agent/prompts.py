from __future__ import annotations

from src.features.encoder import UserFeatureVector

SYSTEM_PROMPT = """You are an assistant helping an event organiser review algorithmically
proposed social groups. Your job is to explain each group in plain English
so the organiser can decide whether to approve or adjust it.

Be concise and specific. Do not use jargon. Refer to attendees by their
group position (e.g. "the most extroverted member") — never by name or ID."""

USER_PROMPT_TEMPLATE = """Event type: {event_type}
Group label: {group_label}
Group size: {group_size}
Cohesion score: {cohesion_score:.2f} ({fit_label})
Flags: {flags_list}

Member profiles (Big Five proxies, scored 0.0–1.0):
{member_profiles_table}

Write:
1. A 2–3 sentence summary of who this group is.
2. One sentence on why they are (or are not) a good fit for each other.
3. For each flag, one sentence explaining what it means in plain English.
   If there are no flags, return an empty list.
4. A confidence level: high / medium / low.
5. If confidence is medium or low, one concrete suggestion for improvement.
   Otherwise return null for suggested_action."""

# Likert fields used to derive Big Five proxies for the prompt table.
# Raw Likert scale is 1–5; normalised to [0, 1] as (value - 1) / 4.
_BIG_FIVE_FIELDS = (
    "energised_meeting_people",       # Extraversion proxy
    "keeps_atmosphere_harmonious",    # Agreeableness proxy
    "enjoys_unfamiliar_experiences",  # Openness proxy
    "shows_up_on_time",               # Conscientiousness proxy
    "anxious_in_social_situations",   # Neuroticism proxy
)


def format_member_profiles(
    group_user_ids: list[str],
    fv_map: dict[str, UserFeatureVector],
) -> str:
    """Build a plain-text table of Big Five proxy scores for prompt injection.

    Each row: ``Member N | E:{:.2f} A:{:.2f} O:{:.2f} C:{:.2f} N:{:.2f}``
    Values are normalised [0, 1] from raw_encoded Likert fields (value - 1) / 4.
    """
    rows: list[str] = []
    for i, uid in enumerate(group_user_ids, start=1):
        fv = fv_map.get(uid)
        if fv is None:
            rows.append(f"Member {i} | E:? A:? O:? C:? N:?")
            continue
        raw = fv.raw_encoded
        scores = []
        for field in _BIG_FIVE_FIELDS:
            val = raw.get(field)
            if val is None:
                scores.append(0.5)
            else:
                scores.append(max(0.0, min(1.0, (float(val) - 1) / 4)))
        e, a, o, c, n = scores
        rows.append(f"Member {i} | E:{e:.2f} A:{a:.2f} O:{o:.2f} C:{c:.2f} N:{n:.2f}")
    return "\n".join(rows)
