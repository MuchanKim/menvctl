#!/usr/bin/env python3
"""Build a plan-brief HTML report. Python 3.9+."""
import sys
from brief_core import main

if __name__ == '__main__':
    try:
        main('planning')
    except (ValueError, OSError, UnicodeError) as error:
        print(f'오류: {error}', file=sys.stderr)
        sys.exit(2)
