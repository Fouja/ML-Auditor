"""
Logging middleware for ML-Auditor.
Structured request/response logging for ELK stack.
"""

import logging
import time
import uuid

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("apps.middleware")


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to attach JWT user to request for Django Ninja.
    Extracts user from JWT token if present.
    """

    def process_request(self, request):
        # JWT auth is handled by Django Ninja's JWTAuth
        # This middleware is a placeholder for future custom logic
        return None


class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Middleware to handle exceptions and return consistent error responses.
    """

    def process_exception(self, request, exception):
        """
        Handle exceptions and return JSON error response.
        """
        logger.error(
            "Exception in %s %s: %s",
            getattr(request, "method", "?"),
            getattr(request, "path", "?"),
            str(exception),
            exc_info=True,
            extra={
                "request_method": getattr(request, "method", None),
                "request_path": getattr(request, "path", None),
                "user_id": str(
                    getattr(request, "user", None) and request.user.id or ""
                ),
                "exception_type": type(exception).__name__,
            },
        )

        if request.path.startswith("/api/"):
            return JsonResponse(
                {
                    "error": {
                        "message": str(exception),
                        "type": type(exception).__name__,
                        "path": request.path,
                        "method": request.method,
                    }
                },
                status=500,
            )

        return None


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.rate_limit_cache = {}

    def process_request(self, request):
        """
        Check rate limits.
        """
        # TODO: Implement proper rate limiting with Redis
        return None


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all requests with structured data for ELK.
    """

    def process_request(self, request):
        request._start_time = time.time()
        request._log_id = str(uuid.uuid4())[:8]
        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        return None

    def process_response(self, request, response):
        duration_ms = 0
        if hasattr(request, "_start_time"):
            duration_ms = round((time.time() - request._start_time) * 1000, 2)

        log_data = {
            "request_method": getattr(request, "method", "?"),
            "request_path": getattr(request, "path", "?"),
            "status_code": response.status_code,
            "response_time": duration_ms,
            "ip_address": self._get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            "content_length": response.get("Content-Length", 0),
            "log_id": getattr(request, "_log_id", ""),
        }

        user = getattr(request, "user", None)
        if user and hasattr(user, "id") and user.is_authenticated:
            log_data["user_id"] = str(user.id)
            log_data["user_email"] = user.email

        if response.status_code >= 500:
            logger.error(
                "%s %s %s %sms",
                log_data["request_method"],
                log_data["request_path"],
                response.status_code,
                duration_ms,
                extra=log_data,
            )
        elif response.status_code >= 400:
            logger.warning(
                "%s %s %s %sms",
                log_data["request_method"],
                log_data["request_path"],
                response.status_code,
                duration_ms,
                extra=log_data,
            )
        elif response.status_code >= 300:
            logger.info(
                "%s %s %s %sms",
                log_data["request_method"],
                log_data["request_path"],
                response.status_code,
                duration_ms,
                extra=log_data,
            )
        else:
            logger.info(
                "%s %s %s %sms",
                log_data["request_method"],
                log_data["request_path"],
                response.status_code,
                duration_ms,
                extra=log_data,
            )

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
