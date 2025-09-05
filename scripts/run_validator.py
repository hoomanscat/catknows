#!/usr/bin/env python3
"""Run SchemaValidator.validate_reports for a tenant and print results."""
import sys
from skoolhud.ai.agents.validator import SchemaValidator


def main(argv):
    if len(argv) < 2:
        print("Usage: run_validator.py <tenant>")
        return 2
    tenant = argv[1]
    ok, errors = SchemaValidator().validate_reports(tenant)
    print("OK:", ok)
    if errors:
        print('\n'.join(errors))
    else:
        print('No errors/warnings')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
