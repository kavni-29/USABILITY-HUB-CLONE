import re


CHOICE_TYPES = {"single_choice", "multiple_choice", "preference"}
QUESTION_TYPES = CHOICE_TYPES | {"rating", "text_response", "yes_no"}
METHODOLOGIES = {"general", "first_click", "preference", "concept_test", "survey"}


def validate_question_form(form):
    prompt = form.get("prompt", "").strip()
    kind = form.get("question_type", "")
    helper_text = form.get("helper_text", "").strip()
    options = [line.strip() for line in form.get("options", "").splitlines() if line.strip()]
    if not prompt or len(prompt) > 500 or len(helper_text) > 300 or kind not in QUESTION_TYPES:
        raise ValueError("Enter a valid question, helper text, and supported question type.")
    if kind in CHOICE_TYPES:
        if not 2 <= len(options) <= 10 or any(len(item) > 160 for item in options):
            raise ValueError("Choice questions need 2–10 options, each no longer than 160 characters.")
        if len({item.casefold() for item in options}) != len(options):
            raise ValueError("Answer options must be unique.")
    elif kind == "yes_no":
        options = ["Yes", "No"]
    elif kind == "text_response":
        options = []
    try:
        low = int(form.get("rating_min", "1"))
        high = int(form.get("rating_max", "5"))
    except ValueError as error:
        raise ValueError("Rating bounds must be whole numbers.") from error
    if kind == "rating" and not 1 <= low < high <= 10:
        raise ValueError("Rating ranges must be within 1–10 and minimum must be less than maximum.")
    if kind != "rating":
        low = high = None
    return {
        "prompt": prompt,
        "question_type": kind,
        "helper_text": helper_text,
        "options": options,
        "rating_min": low,
        "rating_max": high,
        "required": form.get("required") == "on",
    }


def normalize_text_answer(raw):
    value = raw.strip()
    if len(value) > 500 or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", value):
        raise ValueError("Text answers must be 500 characters or fewer and contain no control characters.")
    return value
