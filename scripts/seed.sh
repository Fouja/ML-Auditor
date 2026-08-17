#!/usr/bin/env bash
# ML-Auditor Database Seeding Script
# Creates demo data for testing

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== ML-Auditor Database Seeding ==="

docker compose -f "$PROJECT_DIR/docker-compose.yml" exec -T backend python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.workspace.models import Task, CalendarEvent
from apps.integrations.models import IntegrationConnection
from apps.agents.services.notifications import NotificationPreferences
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

# Create demo user
user, created = User.objects.get_or_create(
    email='demo@mlauditor.com',
    defaults={
        'username': 'demo',
        'first_name': 'Demo',
        'last_name': 'User',
        'is_active': True,
    }
)
if created:
    user.set_password('demo123')
    user.save()
    print(f'Created user: {user.email}')
else:
    print(f'User exists: {user.email}')

# Create tasks
tasks_data = [
    {'title': 'Review bank statements', 'status': 'todo', 'priority': 'high', 'tags': ['finance', 'monthly']},
    {'title': 'Prepare quarterly report', 'status': 'in_progress', 'priority': 'critical', 'tags': ['finance', 'report']},
    {'title': 'Follow up with Plaid support', 'status': 'todo', 'priority': 'medium', 'tags': ['integrations']},
    {'title': 'Update email IMAP config', 'status': 'done', 'priority': 'low', 'tags': ['email', 'config']},
    {'title': 'Analyze Kijiji market trends', 'status': 'review', 'priority': 'high', 'tags': ['kijiji', 'analysis']},
    {'title': 'Monitor Canva competitors', 'status': 'in_progress', 'priority': 'medium', 'tags': ['canva', 'competitors']},
    {'title': 'Schedule dentist appointment', 'status': 'todo', 'priority': 'medium', 'tags': ['calendar', 'personal']},
    {'title': 'Fix WebSocket reconnection bug', 'status': 'in_progress', 'priority': 'high', 'tags': ['bug', 'frontend']},
]

for t in tasks_data:
    Task.objects.get_or_create(
        user=user,
        title=t['title'],
        defaults={
            'status': t['status'],
            'priority': t['priority'],
            'tags': t['tags'],
            'due_date': timezone.now() + timedelta(days=7),
        }
    )
print(f'Created {len(tasks_data)} tasks')

# Create calendar events
now = timezone.now()
events_data = [
    {'title': 'Team standup', 'start': now + timedelta(hours=2), 'end': now + timedelta(hours=2, minutes=30), 'location': 'Zoom'},
    {'title': 'Bank review meeting', 'start': now + timedelta(days=1, hours=10), 'end': now + timedelta(days=1, hours=11), 'location': 'Office'},
    {'title': 'Dentist appointment', 'start': now + timedelta(days=3, hours=14), 'end': now + timedelta(days=3, hours=15), 'location': 'Dental Clinic'},
    {'title': 'Kijiji pickup', 'start': now + timedelta(days=2, hours=16), 'end': now + timedelta(days=2, hours=17), 'location': 'Seller address'},
]

for e in events_data:
    CalendarEvent.objects.get_or_create(
        user=user,
        title=e['title'],
        defaults={
            'start_time': e['start'],
            'end_time': e['end'],
            'location': e['location'],
        }
    )
print(f'Created {len(events_data)} calendar events')

# Notification preferences
NotificationPreferences.update_preferences(user, {
    'email_notifications': True,
    'push_notifications': True,
})
print('Set notification preferences')

print('=== Seeding complete ===')
print(f'Demo login: demo@mlauditor.com / demo123')
"
