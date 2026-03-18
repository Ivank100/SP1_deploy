"""This file defines instructor dashboard endpoints.
It gathers instructor-facing data summaries that combine course and lecture analytics."""


from fastapi import APIRouter, HTTPException, Query, status, Depends
from typing import Optional, List

from ...db.postgres import get_instructor_assigned_course_ids
from ...services.analytics import (
    cluster_questions,
    get_query_trends,
    get_lecture_health_metrics,
    get_all_queries,
)
from ..dependencies.auth import get_current_instructor
from ..schemas import ErrorResponse

router = APIRouter(prefix="/api/instructor", tags=["instructor"])


def get_instructor_assigned_courses(instructor_id: int) -> Optional[List[int]]:
    """Get list of course IDs assigned to an instructor, or None if no assignments exist."""
    return get_instructor_assigned_course_ids(instructor_id)


@router.get("/analytics/query-clusters")
async def get_query_clusters(
    n_clusters: int = Query(5, ge=2, le=20),
    lecture_id: Optional[int] = None,
    course_id: Optional[int] = None,
    current_user: dict = Depends(get_current_instructor),
):
    """
    Get clustered questions to identify common topics/confusion points.
    """
    # Filter by assigned courses for instructors
    if current_user["role"] == "instructor":
        assigned_courses = get_instructor_assigned_courses(current_user["id"])
        if assigned_courses is None:
            # No assignments exist in system yet, show all (backward compatibility)
            # If course_id is specified, filter by it; otherwise show all courses
            queries = get_all_queries(limit=500, lecture_id=lecture_id, course_id=course_id)
        elif len(assigned_courses) == 0:
            # Assignments exist but instructor has none, show nothing
            return {"clusters": [], "total_questions": 0}
        else:
            # Instructor has assigned courses
            if course_id:
                # Specific course requested
                if course_id not in assigned_courses:
                    return {"clusters": [], "total_questions": 0}
                # Only show queries from this specific course (and lecture if specified)
                queries = get_all_queries(limit=500, lecture_id=lecture_id, course_id=course_id)
            else:
                # No course_id specified (All Courses) - show all assigned courses
                # When lecture_id is None, show all lectures; when specified, filter by lecture across all assigned courses
                all_queries = []
                for cid in assigned_courses:
                    course_queries = get_all_queries(limit=500, lecture_id=lecture_id, course_id=cid)
                    all_queries.extend(course_queries)
                queries = all_queries[:500]
    else:
        # Instructor - show all queries (filtered by course_id/lecture_id if specified)
        queries = get_all_queries(limit=500, lecture_id=lecture_id, course_id=course_id)
    
    questions = [q["question"] for q in queries if q["question"]]

    if not questions:
        return {"clusters": [], "total_questions": 0}

    clusters = cluster_questions(questions, n_clusters=n_clusters)

    return {
        "clusters": clusters,
        "total_questions": len(questions),
    }


@router.get("/analytics/trends")
async def get_trends(
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("day", pattern="^(day|week)$"),
    course_id: Optional[int] = None,
    lecture_id: Optional[int] = None,
    current_user: dict = Depends(get_current_instructor),
):
    """
    Get query trends over time.
    """
    # For instructors, filter by assigned courses
    assigned_course_ids = None
    if current_user["role"] == "instructor":
        assigned_courses = get_instructor_assigned_courses(current_user["id"])
        if assigned_courses is None:
            # No assignments exist, show all (backward compatibility)
            # If course_id specified, filter to that course; otherwise show all courses
            assigned_course_ids = [course_id] if course_id else None
        elif len(assigned_courses) == 0:
            # Assignments exist but instructor has none
            return {"trends": [], "period": group_by, "days": days}
        else:
            # Instructor has assigned courses
            if course_id:
                # Specific course requested
                if course_id not in assigned_courses:
                    return {"trends": [], "period": group_by, "days": days}
                # Filter to only this specific course (lecture_id will be handled by get_query_trends)
                assigned_course_ids = [course_id]
            else:
                # No course_id specified (All Courses) - show all assigned courses
                # lecture_id will be handled by get_query_trends
                assigned_course_ids = assigned_courses
    
    # If course_id specified, filter to that course
    if course_id:
        assigned_course_ids = [course_id]
    
    trends = get_query_trends(days=days, group_by=group_by, course_ids=assigned_course_ids, lecture_id=lecture_id)
    return {
        "trends": trends,
        "period": group_by,
        "days": days,
    }


@router.get("/analytics/lecture-health")
async def get_lecture_health(
    course_id: Optional[int] = None,
    lecture_id: Optional[int] = None,
    current_user: dict = Depends(get_current_instructor),
):
    """
    Get health metrics for all lectures: query counts, complexity, confusing topics.
    """
    # For instructors, filter by assigned courses
    assigned_course_ids = None
    if current_user["role"] == "instructor":
        assigned_courses = get_instructor_assigned_courses(current_user["id"])
        if assigned_courses is None:
            # No assignments exist, show all (backward compatibility)
            # If course_id specified, filter to that course; otherwise show all courses
            assigned_course_ids = [course_id] if course_id else None
        elif len(assigned_courses) == 0:
            # Assignments exist but instructor has none
            return {"lectures": [], "total_lectures": 0}
        else:
            # Instructor has assigned courses
            if course_id:
                # Specific course requested
                if course_id not in assigned_courses:
                    return {"lectures": [], "total_lectures": 0}
                # Filter to only this specific course (lecture_id will be handled by get_lecture_health_metrics)
                assigned_course_ids = [course_id]
            else:
                # No course_id specified (All Courses) - show all assigned courses
                # lecture_id will be handled by get_lecture_health_metrics
                assigned_course_ids = assigned_courses
    
    # If course_id specified, filter to that course
    if course_id:
        assigned_course_ids = [course_id]
    
    metrics = get_lecture_health_metrics(course_ids=assigned_course_ids, lecture_id=lecture_id)
    return {
        "lectures": metrics,
        "total_lectures": len(metrics),
    }


@router.get("/queries")
async def list_all_queries(
    limit: int = Query(100, ge=1, le=1000),
    lecture_id: Optional[int] = None,
    course_id: Optional[int] = None,
    current_user: dict = Depends(get_current_instructor),
):
    """
    Get all student queries with optional filters.
    For instructors, only shows queries from courses they're assigned to.
    """
    # Filter by assigned courses
    if current_user["role"] == "instructor":
        assigned_courses = get_instructor_assigned_courses(current_user["id"])
        
        if assigned_courses is None:
            # No assignments exist in system yet, show all (backward compatibility)
            queries = get_all_queries(limit=limit, lecture_id=lecture_id, course_id=course_id)
            return {
                "queries": queries,
                "total": len(queries),
            }
        elif len(assigned_courses) == 0:
            # Assignments exist but instructor has none, return empty
            return {"queries": [], "total": 0}
        else:
            # Instructor has assigned courses
            if course_id and course_id not in assigned_courses:
                return {"queries": [], "total": 0}
            
            # If course_id specified, use it; otherwise use all assigned courses
            courses_to_query = [course_id] if course_id else assigned_courses
            
            # Get queries for assigned courses
            all_queries = []
            for cid in courses_to_query:
                course_queries = get_all_queries(limit=limit, lecture_id=lecture_id, course_id=cid)
                all_queries.extend(course_queries)
            
            # Sort by created_at and limit
            all_queries.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            all_queries = all_queries[:limit]
            
            return {
                "queries": all_queries,
                "total": len(all_queries),
            }
    
    # Show all queries
    queries = get_all_queries(limit=limit, lecture_id=lecture_id, course_id=course_id)
    return {
        "queries": queries,
        "total": len(queries),
    }
