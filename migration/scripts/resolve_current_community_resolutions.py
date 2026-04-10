import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / 'backend'

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leasemanager_api.settings')

import django

django.setup()

from migration.importers import resolve_current_community_manual_resolutions  # noqa: E402


def main():
    result = resolve_current_community_manual_resolutions()
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()

