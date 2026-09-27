from CNR_app.models import AuditLog

def log_action(user, action, model_name, object_id=None, details=None):
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else None,
        details=details or {},
    )