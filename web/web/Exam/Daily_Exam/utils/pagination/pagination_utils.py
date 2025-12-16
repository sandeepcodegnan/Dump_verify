"""Pagination Utilities - DRY Implementation for Consistent Pagination (SoC)"""
from typing import Dict, List, Any, Optional
from math import ceil

def paginate_data(data: List[Any], page: int = 1, limit: int = 50) -> Dict:
    """
    Centralized pagination utility - DRY implementation
    
    Args:
        data: List of items to paginate
        page: Page number (1-based)
        limit: Items per page
    
    Returns:
        Dict with paginated data and metadata
    """
    # Validate inputs
    page = max(1, page)
    limit = max(1, min(limit, 1000))  # Cap at 1000 for performance
    
    total_count = len(data)
    total_pages = ceil(total_count / limit) if total_count > 0 else 1
    
    # Calculate pagination bounds
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    
    # Get paginated slice
    paginated_data = data[start_idx:end_idx]
    
    return {
        "data": paginated_data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_count,
            "totalPages": total_pages,
            "hasNext": page < total_pages,
            "hasPrev": page > 1
        }
    }

def get_pagination_params(page_param: Optional[str], limit_param: Optional[str]) -> tuple:
    """
    Extract and validate pagination parameters - DRY utility
    
    Args:
        page_param: Page parameter as string
        limit_param: Limit parameter as string
    
    Returns:
        Tuple of (page, limit) as integers
    """
    try:
        page = int(page_param) if page_param else 1
        page = max(1, page)
    except (ValueError, TypeError):
        page = 1
    
    try:
        limit = int(limit_param) if limit_param else 10
        limit = max(1, min(limit, 1000))  # Cap at 1000
    except (ValueError, TypeError):
        limit = 10
    
    return page, limit

def build_paginated_response(
    success: bool,
    data: List[Any], 
    page: int, 
    limit: int,
    additional_fields: Optional[Dict] = None
) -> Dict:
    """
    Build standardized paginated response - DRY utility
    
    Args:
        success: Success status
        data: Data to paginate
        page: Page number
        limit: Items per page
        additional_fields: Extra fields to include in response
    
    Returns:
        Standardized paginated response
    """
    paginated_result = paginate_data(data, page, limit)
    
    response = {
        "success": success,
        **paginated_result
    }
    
    if additional_fields:
        response.update(additional_fields)
    
    return response