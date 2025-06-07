"""
REST API endpoints for bulk interview operations.

This module provides endpoints for interviewers to:
1. Bulk upload and process multiple interview recordings for analysis
2. Monitor bulk processing status and retrieve results
3. Track progress for long-running operations

These endpoints are intended for interviewers who need to process multiple
interview recordings at once for analysis and insights.
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import asyncio
import uuid
from datetime import datetime
import json

from app.api.dependencies import db_dependency, active_user_dependency
from app.core.database.models import User
from backup.integrated_interview_service import IntegratedInterviewService
from app.schemas.interview_schemas import InterviewAnalysisResponse

# Create router
router = APIRouter()

# ==========================================
# Schemas for Bulk Operations
# ==========================================

class BulkJobCreate(BaseModel):
    """Schema for creating a bulk processing job."""
    job_name: Optional[str] = None
    enable_stress_analysis: bool = True
    enable_authenticity_analysis: bool = True
    transcription_quality_upgrade: bool = True
    save_results: bool = True

class BulkJobStatus(BaseModel):
    """Schema for bulk job status."""
    job_id: str
    job_name: Optional[str]
    status: str  # "pending", "processing", "completed", "failed", "partial"
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_files: int
    processed_files: int
    successful_files: int
    failed_files: int
    progress_percentage: float
    estimated_time_remaining: Optional[str] = None
    current_file: Optional[str] = None
    error_message: Optional[str] = None

class BulkFileResult(BaseModel):
    """Schema for individual file result in bulk."""
    filename: str
    status: str  # "success", "failed", "processing"
    file_size_mb: float
    processing_time_seconds: Optional[float] = None
    transcription_result: Optional[Dict[str, Any]] = None
    analysis_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class BulkJobResponse(BaseModel):
    """Schema for complete bulk job response."""
    job_info: BulkJobStatus
    file_results: List[BulkFileResult]
    summary: Dict[str, Any]

class BulkJobCreateResponse(BaseModel):
    """Schema for bulk job creation response."""
    job_id: str
    status: str
    message: str
    total_files: int

# ==========================================
# In-Memory Storage for Demo
# (In production, use Redis or database)
# ==========================================

# Store bulk jobs and their status
bulk_jobs: Dict[str, Dict[str, Any]] = {}

# ==========================================
# Bulk Processing Endpoints
# ==========================================

@router.post("/bulk-analysis/upload", response_model=BulkJobCreateResponse)
async def create_bulk_analysis_job(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Multiple interview files to analyze"),
    job_name: Optional[str] = Form(None, description="Optional name for the bulk analysis job"),
    role: str = Form("Candidate", description="Role being interviewed for"),
    company: str = Form("Company", description="Company conducting the interview"),
    interview_type: str = Form("Interview", description="Type of interview"),
    enable_stress_analysis: bool = Form(True),
    enable_authenticity_analysis: bool = Form(True),
    transcription_quality_upgrade: bool = Form(True),
    save_results: bool = Form(True),
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Create a new bulk analysis job for multiple interview recordings.
    
    This endpoint allows interviewers to:
    1. Upload multiple interview recordings at once
    2. Process them for transcription and analysis
    3. Get comprehensive insights across multiple interviews
    4. Monitor progress of bulk operations
    
    Supports various audio/video formats: mp4, mov, avi, wav, mp3, m4a, etc.
    """
    # Validate files
    if not files or len(files) == 0:
        raise HTTPException(status_code=400, detail="At least one file must be provided")
    
    if len(files) > 50:  # Reasonable limit
        raise HTTPException(status_code=400, detail="Maximum 50 files allowed per bulk job")
    
    # Validate file types
    allowed_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.wav', '.mp3', '.m4a', '.flac', '.ogg'}
    for file in files:
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file.filename}. Supported: {', '.join(allowed_extensions)}"
            )
    
    # Create bulk job
    job_id = str(uuid.uuid4())
    
    # Store job metadata
    bulk_jobs[job_id] = {
        "job_id": job_id,
        "job_name": job_name or f"Bulk Analysis Job {job_id[:8]}",
        "status": "pending",
        "created_at": datetime.now(),
        "started_at": None,
        "completed_at": None,
        "total_files": len(files),
        "processed_files": 0,
        "successful_files": 0,
        "failed_files": 0,
        "progress_percentage": 0.0,
        "current_file": None,
        "error_message": None,
        "file_results": [],
        "user_id": current_user.id,
        "processing_params": {
            "role": role,
            "company": company,
            "interview_type": interview_type,
            "enable_stress_analysis": enable_stress_analysis,
            "enable_authenticity_analysis": enable_authenticity_analysis,
            "transcription_quality_upgrade": transcription_quality_upgrade,
            "save_results": save_results
        }
    }
    
    # Read file contents for background processing
    file_data = []
    for file in files:
        content = await file.read()
        file_data.append({
            "filename": file.filename,
            "content": content,
            "size_mb": len(content) / 1024 / 1024
        })
    
    # Start background processing
    background_tasks.add_task(process_bulk_job, job_id, file_data)
    
    return BulkJobCreateResponse(
        job_id=job_id,
        status="pending",
        message=f"Bulk analysis job created with {len(files)} files. Use the job_id to check status.",
        total_files=len(files)
    )

@router.get("/bulk-analysis/{job_id}/status", response_model=BulkJobStatus)
def get_bulk_job_status(
    job_id: str,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Get the current status of a bulk analysis job.
    
    Returns detailed information about:
    - Overall job progress
    - Number of files processed
    - Current processing status
    - Estimated time remaining
    """
    if job_id not in bulk_jobs:
        raise HTTPException(status_code=404, detail="Bulk analysis job not found")
    
    job_data = bulk_jobs[job_id]
    
    # Check user access
    if job_data["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this bulk analysis job")
    
    return BulkJobStatus(
        job_id=job_data["job_id"],
        job_name=job_data["job_name"],
        status=job_data["status"],
        created_at=job_data["created_at"],
        started_at=job_data.get("started_at"),
        completed_at=job_data.get("completed_at"),
        total_files=job_data["total_files"],
        processed_files=job_data["processed_files"],
        successful_files=job_data["successful_files"],
        failed_files=job_data["failed_files"],
        progress_percentage=job_data["progress_percentage"],
        current_file=job_data.get("current_file"),
        error_message=job_data.get("error_message")
    )

@router.get("/bulk-analysis/{job_id}/results", response_model=BulkJobResponse)
def get_bulk_job_results(
    job_id: str,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Get complete results for a bulk analysis job.
    
    Returns:
    - Job status and metadata
    - Individual file processing results
    - Summary statistics
    - Error details for failed files
    """
    if job_id not in bulk_jobs:
        raise HTTPException(status_code=404, detail="Bulk analysis job not found")
    
    job_data = bulk_jobs[job_id]
    
    # Check user access
    if job_data["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this bulk analysis job")
    
    # Build file results
    file_results = []
    for result in job_data.get("file_results", []):
        file_results.append(BulkFileResult(**result))
    
    # Build summary
    summary = {
        "total_files": job_data["total_files"],
        "successful_files": job_data["successful_files"],
        "failed_files": job_data["failed_files"],
        "success_rate": (job_data["successful_files"] / job_data["total_files"] * 100) if job_data["total_files"] > 0 else 0,
        "total_processing_time": sum(r.get("processing_time_seconds") or 0 for r in job_data.get("file_results", [])),
        "average_file_size_mb": sum(r.get("file_size_mb") or 0 for r in job_data.get("file_results", [])) / max(len(job_data.get("file_results", [])), 1),
        "estimated_cost": job_data["successful_files"] * 0.02  # Rough estimate based on transcription costs
    }
    
    # Create job status
    job_status = BulkJobStatus(
        job_id=job_data["job_id"],
        job_name=job_data["job_name"],
        status=job_data["status"],
        created_at=job_data["created_at"],
        started_at=job_data.get("started_at"),
        completed_at=job_data.get("completed_at"),
        total_files=job_data["total_files"],
        processed_files=job_data["processed_files"],
        successful_files=job_data["successful_files"],
        failed_files=job_data["failed_files"],
        progress_percentage=job_data["progress_percentage"],
        current_file=job_data.get("current_file"),
        error_message=job_data.get("error_message")
    )
    
    return BulkJobResponse(
        job_info=job_status,
        file_results=file_results,
        summary=summary
    )

@router.get("/bulk-analysis", response_model=List[BulkJobStatus])
def list_bulk_jobs(
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    List all bulk analysis jobs for the current user.
    
    Returns a summary of all jobs with their current status.
    Useful for monitoring multiple bulk operations.
    """
    job_list = []
    for job_data in bulk_jobs.values():
        # Only show jobs for the current user
        if job_data.get("user_id") == current_user.id:
            job_list.append(BulkJobStatus(
                job_id=job_data["job_id"],
                job_name=job_data["job_name"],
                status=job_data["status"],
                created_at=job_data["created_at"],
                started_at=job_data.get("started_at"),
                completed_at=job_data.get("completed_at"),
                total_files=job_data["total_files"],
                processed_files=job_data["processed_files"],
                successful_files=job_data["successful_files"],
                failed_files=job_data["failed_files"],
                progress_percentage=job_data["progress_percentage"],
                current_file=job_data.get("current_file"),
                error_message=job_data.get("error_message")
            ))
    
    return sorted(job_list, key=lambda x: x.created_at, reverse=True)

@router.delete("/bulk-analysis/{job_id}")
def cancel_bulk_job(
    job_id: str,
    db: Session = db_dependency,
    current_user: User = active_user_dependency
):
    """
    Cancel a bulk analysis job.
    
    Note: Currently running file processing cannot be stopped immediately,
    but no new files will be processed after cancellation.
    """
    if job_id not in bulk_jobs:
        raise HTTPException(status_code=404, detail="Bulk analysis job not found")
    
    job_data = bulk_jobs[job_id]
    
    # Check user access
    if job_data["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this bulk analysis job")
    
    if job_data["status"] in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed or failed job")
    
    job_data["status"] = "cancelled"
    job_data["completed_at"] = datetime.now()
    
    return {"message": f"Bulk analysis job {job_id} has been cancelled"}

# ==========================================
# Background Processing Function
# ==========================================

async def process_bulk_job(job_id: str, file_data: List[Dict[str, Any]]):
    """
    Background task to process all files in a bulk analysis job.
    """
    job_data = bulk_jobs[job_id]
    
    try:
        # Mark job as started
        job_data["status"] = "processing"
        job_data["started_at"] = datetime.now()
        
        # Initialize integrated service
        integrated_service = IntegratedInterviewService()
        processing_params = job_data["processing_params"]
        
        # Process each file
        for i, file_info in enumerate(file_data):
            # Check if job was cancelled
            if job_data["status"] == "cancelled":
                break
                
            filename = file_info["filename"]
            content = file_info["content"]
            size_mb = file_info["size_mb"]
            
            # Update current file being processed
            job_data["current_file"] = filename
            
            file_result = {
                "filename": filename,
                "status": "processing",
                "file_size_mb": size_mb,
                "processing_time_seconds": None,
                "transcription_result": None,
                "analysis_result": None,
                "error_message": None
            }
            
            try:
                start_time = datetime.now()
                
                # Process the file
                result = integrated_service.process_interview_file(
                    file_name=filename,
                    file_content=content,
                    context={
                        "role": processing_params["role"],
                        "company": processing_params["company"],
                        "interview_type": processing_params["interview_type"]
                    },
                    options={
                        "use_quality_upgrade": processing_params["transcription_quality_upgrade"],
                        "enable_stress_analysis": processing_params["enable_stress_analysis"],
                        "enable_authenticity_analysis": processing_params["enable_authenticity_analysis"],
                        "save_results": processing_params["save_results"]
                    }
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                # Update file result
                file_result.update({
                    "status": "success",
                    "processing_time_seconds": processing_time,
                    "transcription_result": result.get("transcription"),
                    "analysis_result": result.get("analysis")
                })
                
                job_data["successful_files"] += 1
                
            except Exception as e:
                # Handle file processing error
                file_result.update({
                    "status": "failed",
                    "error_message": str(e)
                })
                job_data["failed_files"] += 1
                
            # Add file result to job
            job_data["file_results"].append(file_result)
            job_data["processed_files"] += 1
            
            # Update progress
            job_data["progress_percentage"] = (job_data["processed_files"] / job_data["total_files"]) * 100
            
        # Mark job as completed
        if job_data["status"] != "cancelled":
            if job_data["failed_files"] == 0:
                job_data["status"] = "completed"
            elif job_data["successful_files"] > 0:
                job_data["status"] = "partial"
            else:
                job_data["status"] = "failed"
                
        job_data["completed_at"] = datetime.now()
        job_data["current_file"] = None
        
    except Exception as e:
        # Handle job-level error
        job_data["status"] = "failed"
        job_data["error_message"] = str(e)
        job_data["completed_at"] = datetime.now()
        job_data["current_file"] = None
