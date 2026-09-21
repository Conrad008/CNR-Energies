#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

python manage.py seedData

python manage.py shell -c "
from core.models import User;
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin@cnrenergies.com', 'Ngeno208', role='SUPER_ADMIN')
    print('Superuser created successfully.')
"