import time
import logging
import threading

access_logger = logging.getLogger("http.access")

# Contexto thread-local para que signals puedan saber "quién" actuó
_request_ctx = threading.local()

def set_request(request):
    _request_ctx.request = request

def get_request():
    return getattr(_request_ctx, "request", None)

class AccessLogMiddleware:
    """
    Loguea cada request con método, path, status, usuario y duración en ms.
    Expone el request en thread-local para que los signals puedan leer el usuario.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_request(request)  # deja accesible el request para signals
        start = time.perf_counter()
        try:
            response = self.get_response(request)
            status = getattr(response, "status_code", 500)
            return response
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            user = getattr(request, "user", None)
            user_repr = user.username if (user and user.is_authenticated) else "anonymous"

            access_logger.info(
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.get_full_path(),
                    "status": status,
                    "user": user_repr,
                    "duration_ms": duration_ms,
                },
            )
            # Limpieza (evita fugas si hay reuso de threads)
            set_request(None)
