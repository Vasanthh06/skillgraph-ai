from ml.evaluation.metrics import evaluate, ndcg_at_k, recall_at_k, split_by_user
from ml.preprocessing.build_dataset import next_item_examples, sequences, user_skill_pairs
from ml.ranking.rank import blend


def ev(i, u, s, t="skill_search"):
    return {"id": i, "user_id": u, "event_type": t, "meta": {"skill": s}}


def test_sequences_ordered_deduped_and_thresholded():
    events = [ev(3, 1, "pandas"), ev(1, 1, "python"), ev(2, 1, "python"), ev(4, 1, "numpy"), ev(5, 2, "git"), {"id": 6, "user_id": 2, "event_type": "login", "meta": {}}]
    s = sequences(events)
    assert s == {1: ["python", "pandas", "numpy"]}  # user 2 too short, login ignored, repeat collapsed


def test_no_activity_means_no_training_data():
    assert sequences([]) == {} and next_item_examples({}) == [] and user_skill_pairs({}) == []


def test_next_item_examples():
    assert next_item_examples({1: ["a", "b", "c"]}) == [(["a"], "b"), (["a", "b"], "c")]


def test_metrics():
    assert recall_at_k(["a", "b"], "b", 1) == 0.0 and recall_at_k(["a", "b"], "b", 2) == 1.0
    assert ndcg_at_k(["a", "b"], "a", 5) == 1.0 and 0 < ndcg_at_k(["a", "b"], "b", 5) < 1
    res = evaluate(lambda h: ["x", "y"], [(["q"], "x"), (["q"], "z")], k=2)
    assert res["recall@2"] == 0.5
    assert evaluate(lambda h: [], [])["n"] == 0


def test_leave_last_out_no_leakage():
    train, test = split_by_user({1: ["a", "b", "c", "d"]})
    assert train[1] == ["a", "b", "c"] and test == [(["a", "b", "c"], "d")]


def test_blend_degrades_to_rules_and_respects_eligibility():
    r = blend(["a", "b", "c"], {"a": 1, "b": 3, "c": 2})
    assert [x["id"] for x in r] == ["b", "c", "a"] and set(r[0]["signals"]) == {"rules"}
    r2 = blend(["a", "b"], {"a": 1, "b": 1}, sasrec={"a": 0.1, "b": 0.9}, eligible={"a"})
    assert [x["id"] for x in r2] == ["a"]
    r3 = blend(["a", "b"], {"a": 1, "b": 1}, sasrec={"a": 0.1, "b": 0.9})
    assert r3[0]["id"] == "b" and set(r3[0]["signals"]) == {"rules", "sasrec"}
