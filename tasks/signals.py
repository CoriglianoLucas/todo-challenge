import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from .models import Task
from .middleware import get_request

logger = logging.getLogger("tasks")

def actor_username():
    req = get_request()
    if req and getattr(req, "user", None) and req.user.is_authenticated:
        return req.user.username
    return "system"

@receiver(pre_save, sender=Task)
def task_pre_save(sender, instance: Task, **kwargs):
    if instance.pk:
        try:
            old = Task.objects.get(pk=instance.pk)
            instance._was_completed = old.completed
        except Task.DoesNotExist:
            instance._was_completed = False
    else:
        instance._was_completed = False

@receiver(post_save, sender=Task)
def task_post_save(sender, instance: Task, created, **kwargs):
    user = actor_username()
    if created:
        logger.info(f"task created by {user}", extra={"task_id": instance.id})
    else:
        was_completed = getattr(instance, "_was_completed", instance.completed)
        if not was_completed and instance.completed:
            logger.info(f"task completed by {user}", extra={"task_id": instance.id})
        elif was_completed and not instance.completed:
            logger.info(f"task uncompleted by {user}", extra={"task_id": instance.id})
        else:
            logger.info(f"task updated by {user}", extra={"task_id": instance.id})

@receiver(post_delete, sender=Task)
def task_post_delete(sender, instance: Task, **kwargs):
    user = actor_username()
    logger.info(f"task deleted by {user}", extra={"task_id": instance.id})
