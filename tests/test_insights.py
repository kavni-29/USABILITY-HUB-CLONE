from types import SimpleNamespace

from app.insights import generate_question_insights
from app.analytics import safe_csv_cell


def test_option_insight_reports_tie_and_sample_size():
    question = SimpleNamespace(question_type="preference", options=[SimpleNamespace(id=1, label="A"), SimpleNamespace(id=2, label="B")])
    answers = [SimpleNamespace(option_id=1, response_id=10), SimpleNamespace(option_id=2, response_id=11)]
    insight = generate_question_insights(question, answers)[0]
    assert "tied" in insight["statement"]
    assert insight["sample_size"] == 2
    assert "Small sample" in insight["caveat"]


def test_rating_insight_includes_mean_median_and_empty_handling():
    question = SimpleNamespace(question_type="rating", rating_max=5)
    answers = [SimpleNamespace(value="1", response_id=1), SimpleNamespace(value="5", response_id=2)]
    insight = generate_question_insights(question, answers)[0]
    assert insight["metric"] == "mean=3.00; median=3; most common rating(s)=1 and 5"
    assert generate_question_insights(question, []) == []


def test_csv_cells_escape_formula_markers_after_whitespace():
    assert safe_csv_cell("=1+1") == "'=1+1"
    assert safe_csv_cell("  =1+1") == "'  =1+1"
    assert safe_csv_cell("plain text") == "plain text"
