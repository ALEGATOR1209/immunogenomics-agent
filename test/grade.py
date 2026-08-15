#!/usr/bin/env python3
import json
import sys


def _normalize_item(item):
    return item.strip().lower() if isinstance(item, str) else item


def list_overlap_score(actual, expected):
    """Jaccard-style partial credit: |correct| / (|ground_truth| + |incorrect guesses|)."""
    if isinstance(actual, str):
        actual = [actual]
    if not isinstance(actual, list):
        return 0.0

    expected_set = {_normalize_item(x) for x in expected}
    actual_set = {_normalize_item(x) for x in actual}
    n_correct = len(expected_set & actual_set)
    n_incorrect = len(actual_set - expected_set)

    denominator = len(expected_set) + n_incorrect
    return (n_correct / denominator) if denominator else 0.0


def field_score(actual, expected, tolerance):
    """Returns (score in [0, 1], correct: bool) for one field."""
    tolerance_type = tolerance.get("type") if tolerance else None

    if tolerance_type == "list_overlap":
        score = list_overlap_score(actual, expected)
        return score, score == 1.0

    if tolerance is None:
        if isinstance(actual, str) and isinstance(expected, str):
            correct = actual.lower() == expected.lower()
        else:
            correct = actual == expected
        return (1.0 if correct else 0.0), correct

    value = tolerance.get("value", 0)
    if tolerance_type == "absolute":
        try:
            correct = abs(actual - expected) <= value
        except TypeError:
            return 0.0, False
        return (1.0 if correct else 0.0), correct

    raise ValueError(f"Unsupported tolerance type: {tolerance_type!r}")


def grade(task, answer):
    grader_config = task.get("grader", {}).get("config", {})
    ground_truth = grader_config.get("ground_truth", {})
    tolerances = grader_config.get("tolerances", {})

    answer = answer if isinstance(answer, dict) else {}
    expected_keys = set(ground_truth.keys())
    actual_keys = set(answer.keys())

    fields = {}
    for key, expected_value in ground_truth.items():
        if key not in answer:
            fields[key] = {"expected": expected_value, "actual": None, "correct": False, "score": 0.0, "reason": "missing"}
            continue

        actual_value = answer[key]
        try:
            score, correct = field_score(actual_value, expected_value, tolerances.get(key))
            fields[key] = {"expected": expected_value, "actual": actual_value, "correct": correct, "score": score}
        except ValueError as e:
            fields[key] = {"expected": expected_value, "actual": actual_value, "correct": False, "score": 0.0, "reason": str(e)}

    points = sum(f["score"] for f in fields.values())
    total = len(ground_truth)

    return {
        "passed": points == total,
        "points": points,
        "total": total,
        "score": (points / total) if total else None,
        "structure_match": expected_keys == actual_keys,
        "missing_keys": sorted(expected_keys - actual_keys),
        "extra_keys": sorted(actual_keys - expected_keys),
        "fields": fields,
    }


def main():
    if len(sys.argv) not in (3, 4, 5):
        print("Usage: grade.py <task.json> <output.json> [duration_seconds] [skills]", file=sys.stderr)
        sys.exit(2)

    task_json_path, answer_json_path = sys.argv[1], sys.argv[2]
    task = json.loads(open(task_json_path).read())

    result = {}
    try:
        answer = json.loads(open(answer_json_path).read())
    except FileNotFoundError:
        answer = {}
        result["error"] = "output.json was not produced"
    except json.JSONDecodeError as e:
        answer = {}
        result["error"] = f"output.json is not valid JSON: {e}"

    if len(sys.argv) >= 4:
        result["duration_seconds"] = int(sys.argv[3])
    if len(sys.argv) == 5:
        result["skills"] = sys.argv[4].strip().lower() in ("1", "true", "yes", "enabled")

    result.update(grade(task, answer))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
