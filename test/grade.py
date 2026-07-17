#!/usr/bin/env python3
import json
import sys


def within_tolerance(actual, expected, tolerance):
    if tolerance is None:
        if isinstance(actual, str) and isinstance(expected, str):
            return actual.lower() == expected.lower()
        return actual == expected

    tolerance_type = tolerance.get("type")
    value = tolerance.get("value", 0)

    if tolerance_type == "absolute":
        try:
            return abs(actual - expected) <= value
        except TypeError:
            return False

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
            fields[key] = {"expected": expected_value, "actual": None, "correct": False, "reason": "missing"}
            continue

        actual_value = answer[key]
        try:
            correct = within_tolerance(actual_value, expected_value, tolerances.get(key))
            fields[key] = {"expected": expected_value, "actual": actual_value, "correct": correct}
        except ValueError as e:
            fields[key] = {"expected": expected_value, "actual": actual_value, "correct": False, "reason": str(e)}

    points = sum(1 for f in fields.values() if f["correct"])
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
