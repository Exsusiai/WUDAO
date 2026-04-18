# ERR-001: structlog add_logger_name incompatible with PrintLogger

**Date:** 2026-04-15
**Severity:** Medium
**Category:** Python / structlog

## Problem
`structlog.stdlib.add_logger_name` processor raises `AttributeError: 'PrintLogger' object has no attribute 'name'` when used with `structlog.PrintLoggerFactory`.

## Root Cause
`add_logger_name` expects a stdlib `logging.Logger` which has a `.name` attribute. `PrintLogger` (used by `PrintLoggerFactory`) does not have this attribute.

## Fix
Remove `structlog.stdlib.add_logger_name` from the processor chain when using `PrintLoggerFactory`. If logger name is needed, pass it as a bound context variable via `structlog.get_logger(module_name)` instead.

## Prevention
When configuring structlog, only use `stdlib.*` processors if `logger_factory` is `structlog.stdlib.LoggerFactory()`. With `PrintLoggerFactory`, stick to non-stdlib processors.
