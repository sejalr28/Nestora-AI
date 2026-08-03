from fastapi import HTTPException


def not_found(resource: str, resource_id: int | str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource} {resource_id} not found")
