#!/usr/bin/env python3
import json
import sys


def mask(value):
    if isinstance(value, dict):
        return {k: mask(v) for k, v in value.items()}
    if isinstance(value, list):
        return [mask(v) for v in value]
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return 0
    if isinstance(value, float):
        return 0.0
    if value is None:
        return None
    return ""


def main():
    task_json_path, system_md_path = sys.argv[1], sys.argv[2]

    task = json.loads(open(task_json_path).read())
    template = open(system_md_path).read()

    ground_truth = task.get("grader", {}).get("config", {}).get("ground_truth", {})
    output_format = json.dumps(mask(ground_truth), indent=2)

    rendered = template.replace("<TASK>", task["task"]).replace("<OUTPUT_FORMAT>", output_format)
    sys.stdout.write(rendered)


if __name__ == "__main__":
    main()
