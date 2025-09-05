from __future__ import annotations
import argparse
from skoolhud.ai.agents.validator import SchemaValidator


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tenant")
    args = p.parse_args()
    v = SchemaValidator()
    ok, errors = v.validate_reports(args.tenant)
    print("OK:" if ok else "FAILED:")
    for e in errors:
        print("-", e)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
