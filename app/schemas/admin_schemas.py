"""
Admin module specific schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class SystemConfigUpdate(BaseModel):
    """Schema for updating system-wide configuration parameters"""
    rate_limits: Optional[Dict[str, int]] = None
    feature_flags: Optional[Dict[str, bool]] = None
    timeouts: Optional[Dict[str, int]] = None
    storage_paths: Optional[Dict[str, str]] = None
    service_connections: Optional[Dict[str, Dict[str, Any]]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "rate_limits": {
                    "auth": 10,
                    "api": 100
                },
                "feature_flags": {
                    "advanced_analytics": True,
                    "beta_features": False
                }
            }
        }


class SystemStatusResponse(BaseModel):
    """Schema for system status information"""
    status: str
    database: str
    storage: str
    processors: Dict[str, str]
    uptime: str
    version: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "operational",
                "database": "connected",
                "storage": "available",
                "processors": {
                    "transcription": "operational",
                    "analysis": "operational"
                },
                "uptime": "7 days 5 hours",
                "version": "1.0.0"
            }
        }


class MonitoringMetricsResponse(BaseModel):
    """Schema for system monitoring metrics"""
    period: str
    api: Dict[str, Any]
    users: Dict[str, Any]
    resources: Dict[str, Any]
    processing: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "period": "day",
                "api": {
                    "total_requests": 45871,
                    "average_response_time_ms": 182,
                    "error_rate": 0.02,
                    "endpoints": {
                        "/interviews": 15489,
                        "/recordings": 12498,
                        "/auth": 8954,
                        "other": 8930
                    }
                },
                "users": {
                    "active_sessions": 287,
                    "new_registrations": 34,
                    "peak_concurrent_users": 156
                },
                "resources": {
                    "cpu_usage_percent": 42,
                    "memory_usage_percent": 68,
                    "storage_usage_percent": 53,
                    "database_connections": 35
                },
                "processing": {
                    "transcription_jobs": {
                        "completed": 1245,
                        "pending": 23,
                        "failed": 5,
                        "average_duration_seconds": 18
                    },
                    "analysis_jobs": {
                        "completed": 1198,
                        "pending": 12,
                        "failed": 8,
                        "average_duration_seconds": 42
                    }
                }
            }
        }