from collections import Counter
from statistics import mean, median


def generate_question_insights(question, answers):
    """Describe observed answers without implying causality or population inference."""
    if not answers:
        return []
    respondents = len({answer.response_id for answer in answers})
    caveat = "Observed sample only; this does not establish causation or representativeness."
    if respondents < 10:
        caveat = f"Small sample (n={respondents}); interpret cautiously. " + caveat
    if question.question_type == "rating":
        values = [int(answer.value) for answer in answers if answer.value and answer.value.isdigit()]
        if not values:
            return []
        counts = Counter(values)
        popular = max(counts.values())
        modes = sorted(value for value, count in counts.items() if count == popular)
        mode_text = " and ".join(map(str, modes)) if len(modes) < 4 else ", ".join(map(str, modes))
        average = mean(values)
        median_value = median(values)
        return [{
            "statement": f"The average rating was {average:.2f} out of {question.rating_max}; the median was {median_value:g}.",
            "metric": f"mean={average:.2f}; median={median_value:g}; most common rating(s)={mode_text}",
            "sample_size": len(values),
            "explanation": "The mean uses all valid numeric ratings; the median is the middle value (or midpoint of the two middle values).",
            "caveat": caveat,
        }]
    if question.question_type in {"single_choice", "multiple_choice", "preference", "yes_no"}:
        counts = Counter(answer.option_id for answer in answers if answer.option_id is not None)
        if not counts:
            return []
        winning_count = max(counts.values())
        winners = [option.label for option in question.options if counts[option.id] == winning_count]
        winner_text = ", ".join(winners)
        share = winning_count / respondents * 100
        statement = (
            f"{winner_text} received the most selections ({winning_count} selections, {share:.1f}% of respondents)."
            if len(winners) == 1
            else f"The top result was tied between {winner_text} ({winning_count} selections each)."
        )
        return [{
            "statement": statement,
            "metric": f"{winning_count} of {respondents} respondents selected each leading option ({share:.1f}% each)",
            "sample_size": respondents,
            "explanation": "Percentages use respondents who answered this question; for multi-select questions the shares can add to more than 100%.",
            "caveat": caveat,
        }]
    if question.question_type == "text_response":
        count = sum(bool((answer.value or "").strip()) for answer in answers)
        if not count:
            return []
        return [{
            "statement": f"The study received {count} written response{'s' if count != 1 else ''}.",
            "metric": f"{count} non-empty answers out of {respondents} respondents",
            "sample_size": count,
            "explanation": "Written responses are shown individually below and have not been automatically categorized.",
            "caveat": "Read the responses in context; no theme or sentiment inference is claimed.",
        }]
    return []
