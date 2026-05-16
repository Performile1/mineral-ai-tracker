"""
Mineral AI Tracker - Error Handler & Logging
Version: 3.0
Description: Centralized error handling and logging with safe crash handling
"""

import sys
import traceback
import functools
from typing import Callable, Any, Optional
from datetime import datetime
from loguru import logger
from enum import Enum


class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorHandler:
    """
    Centralized error handler with logging and crash handling
    
    Features:
    - Structured error logging
    - Severity classification
    - Safe crash handling
    - Error recovery strategies
    """
    
    def __init__(self, log_file: str = "logs/errors.log"):
        """
        Initialize error handler
        
        Args:
            log_file: Path to error log file
        """
        self.log_file = log_file
        
        # Configure error-specific logger
        logger.add(
            log_file,
            rotation="10 MB",
            retention="30 days",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
            backtrace=True,
            diagnose=True
        )
        
        logger.info("Error handler initialized")
    
    def log_error(
        self,
        error: Exception,
        context: Optional[dict] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        user_id: Optional[str] = None
    ):
        """
        Log an error with context
        
        Args:
            error: Exception object
            context: Additional context dictionary
            severity: Error severity level
            user_id: User ID if applicable
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "severity": severity.value,
            "user_id": user_id,
            "context": context or {}
        }
        
        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR: {error_info}")
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH SEVERITY: {error_info}")
        elif severity == ErrorSeverity.MEDIUM:
            logger.error(f"MEDIUM SEVERITY: {error_info}")
        else:
            logger.warning(f"LOW SEVERITY: {error_info}")
    
    def handle_scraping_error(
        self,
        source: str,
        error: Exception,
        url: Optional[str] = None
    ):
        """
        Handle scraping-specific errors
        
        Args:
            source: Data source name
            error: Exception object
            url: URL that failed
        """
        context = {
            "source": source,
            "url": url,
            "error_type": "scraping_error"
        }
        
        # Classify severity
        if "timeout" in str(error).lower() or "connection" in str(error).lower():
            severity = ErrorSeverity.LOW
        elif "403" in str(error) or "blocked" in str(error).lower():
            severity = ErrorSeverity.HIGH
        else:
            severity = ErrorSeverity.MEDIUM
        
        self.log_error(error, context, severity)
    
    def handle_database_error(
        self,
        operation: str,
        error: Exception,
        table: Optional[str] = None
    ):
        """
        Handle database-specific errors
        
        Args:
            operation: Database operation (insert, update, delete, etc.)
            error: Exception object
            table: Table name
        """
        context = {
            "operation": operation,
            "table": table,
            "error_type": "database_error"
        }
        
        # Database errors are typically high severity
        severity = ErrorSeverity.HIGH
        self.log_error(error, context, severity)
    
    def handle_api_error(
        self,
        endpoint: str,
        error: Exception,
        status_code: Optional[int] = None
    ):
        """
        Handle API-specific errors
        
        Args:
            endpoint: API endpoint
            error: Exception object
            status_code: HTTP status code
        """
        context = {
            "endpoint": endpoint,
            "status_code": status_code,
            "error_type": "api_error"
        }
        
        # Classify severity based on status code
        if status_code:
            if status_code >= 500:
                severity = ErrorSeverity.HIGH
            elif status_code >= 400:
                severity = ErrorSeverity.MEDIUM
            else:
                severity = ErrorSeverity.LOW
        else:
            severity = ErrorSeverity.MEDIUM
        
        self.log_error(error, context, severity)
    
    def safe_execute(
        self,
        func: Callable,
        *args,
        default_return: Any = None,
        log_error: bool = True,
        **kwargs
    ) -> Any:
        """
        Safely execute a function with error handling
        
        Args:
            func: Function to execute
            *args: Function arguments
            default_return: Value to return on error
            log_error: Whether to log errors
            **kwargs: Function keyword arguments
        
        Returns:
            Function result or default_return on error
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if log_error:
                self.log_error(e, {"function": func.__name__})
            return default_return


def safe_crash_handler(exc_type, exc_value, exc_traceback):
    """
    Global exception handler for safe crash handling
    
    Args:
        exc_type: Exception type
        exc_value: Exception value
        exc_traceback: Exception traceback
    """
    logger.critical(
        "FATAL ERROR - System Crash",
        exc_info=(exc_type, exc_value, exc_traceback)
    )
    
    # Log crash details
    logger.critical(f"Exception Type: {exc_type.__name__}")
    logger.critical(f"Exception Message: {exc_value}")
    
    # Attempt to save crash dump
    try:
        crash_dump = {
            "timestamp": datetime.now().isoformat(),
            "exception_type": exc_type.__name__,
            "exception_message": str(exc_value),
            "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        }
        
        with open("logs/crash_dump.log", "a") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"CRASH DUMP: {crash_dump['timestamp']}\n")
            f.write(f"Type: {crash_dump['exception_type']}\n")
            f.write(f"Message: {crash_dump['exception_message']}\n")
            f.write(f"Traceback:\n{crash_dump['traceback']}\n")
        
        logger.info("Crash dump saved to logs/crash_dump.log")
    except Exception as e:
        logger.error(f"Failed to save crash dump: {e}")
    
    # Exit gracefully
    sys.exit(1)


def with_error_handling(
    default_return: Any = None,
    log_error: bool = True,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
):
    """
    Decorator for adding error handling to functions
    
    Args:
        default_return: Value to return on error
        log_error: Whether to log errors
        severity: Error severity level
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    error_handler = ErrorHandler()
                    error_handler.log_error(e, {"function": func.__name__}, severity)
                return default_return
        return wrapper
    return decorator


def with_async_error_handling(
    default_return: Any = None,
    log_error: bool = True,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
):
    """
    Decorator for adding error handling to async functions
    
    Args:
        default_return: Value to return on error
        log_error: Whether to log errors
        severity: Error severity level
    
    Returns:
        Decorated async function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    error_handler = ErrorHandler()
                    error_handler.log_error(e, {"function": func.__name__}, severity)
                return default_return
        return wrapper
    return decorator


# Global error handler instance
error_handler = ErrorHandler()

# Install global exception handler
sys.excepthook = safe_crash_handler
