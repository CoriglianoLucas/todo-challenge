from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User

from tasks.models import Task

class TasksAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.user = User.objects.create_user(username="alice", password="pass123456", email="alice@example.com")
        self.other = User.objects.create_user(username="bob", password="pass123456", email="bob@example.com")

        # URLs (nombres definidos por DRF Router y nuestras vistas)
        self.url_login = reverse("token_obtain_pair")
        self.url_refresh = reverse("token_refresh")
        self.url_register = reverse("register")
        self.url_tasks_list = reverse("tasks-list")

        # Helper: obtener token para self.user
        res = self.client.post(self.url_login, {"username": "alice", "password": "pass123456"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.access = res.data["access"]

        # Setear header Authorization
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_register_success(self):
        # Logout para usar el registro sin credenciales
        client = APIClient()
        payload = {"username": "newuser", "email": "new@user.com", "password": "12345678"}
        res = client.post(self.url_register, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_auth_required_for_tasks(self):
        client = APIClient()
        res = client.get(self.url_tasks_list)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_task(self):
        payload = {"title": "Primera tarea", "description": "detalle"}
        res = self.client.post(self.url_tasks_list, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.filter(user=self.user).count(), 1)
        self.assertEqual(res.data["title"], "Primera tarea")
        self.assertIn("created_at", res.data)
        self.assertFalse(res.data["completed"])

    def test_list_shows_only_user_tasks(self):
        # Tarea de otro usuario
        Task.objects.create(user=self.other, title="Bob task")
        # Tarea del usuario actual
        Task.objects.create(user=self.user, title="Alice task")

        res = self.client.get(self.url_tasks_list)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [t["title"] for t in res.data]
        self.assertIn("Alice task", titles)
        self.assertNotIn("Bob task", titles)

    def test_filter_by_search(self):
        Task.objects.create(user=self.user, title="Comprar pan")
        Task.objects.create(user=self.user, title="Estudiar Django")
        res = self.client.get(self.url_tasks_list, {"search": "comprar"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["title"], "Comprar pan")

    def test_filter_by_created_after(self):
        # Creamos 2 tareas y ajustamos created_at manualmente (auto_now_add requiere update)
        t1 = Task.objects.create(user=self.user, title="Antigua")
        t2 = Task.objects.create(user=self.user, title="Reciente")

        # Forzar fechas
        old_date = timezone.datetime(2025, 8, 1, 12, 0, 0, tzinfo=timezone.get_current_timezone())
        new_date = timezone.datetime(2025, 8, 8, 12, 0, 0, tzinfo=timezone.get_current_timezone())
        Task.objects.filter(pk=t1.pk).update(created_at=old_date)
        Task.objects.filter(pk=t2.pk).update(created_at=new_date)

        res = self.client.get(self.url_tasks_list, {"created_after": "2025-08-05"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = [t["title"] for t in res.data]
        self.assertIn("Reciente", titles)
        self.assertNotIn("Antigua", titles)

    def test_update_task(self):
        task = Task.objects.create(user=self.user, title="Editame")
        url_detail = reverse("tasks-detail", args=[task.id])
        res = self.client.put(url_detail, {"title": "Editada", "description": "", "completed": False}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.title, "Editada")

    def test_mark_complete_action(self):
        task = Task.objects.create(user=self.user, title="Completar")
        # Nombre del endpoint de acción: basename + método @action (mark_complete) => "tasks-mark-complete"
        url_complete = reverse("tasks-complete", args=[task.id])
        res = self.client.put(url_complete, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertTrue(task.completed)

    def test_delete_task(self):
        task = Task.objects.create(user=self.user, title="Borrar")
        url_detail = reverse("tasks-detail", args=[task.id])
        res = self.client.delete(url_detail)
        self.assertIn(res.status_code, (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT))
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_user_cannot_see_others_task(self):
        # Crea tarea de otro usuario y trata de acceder al detail
        other_task = Task.objects.create(user=self.other, title="No deberías verme")
        url_detail = reverse("tasks-detail", args=[other_task.id])
        res = self.client.get(url_detail)
        # DRF por defecto retorna 404 si get_queryset filtra por user
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
