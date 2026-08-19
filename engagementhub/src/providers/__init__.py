"""Providers de canal (S3-BACK-04)."""
from src.providers.base import ChannelProvider, DispatchResult, DeliveryStatus, HealthCheckResult
from src.providers.registry import get_provider, get_provider_by_canal, list_providers
