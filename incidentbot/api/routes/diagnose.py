from fastapi import APIRouter, status

router = APIRouter()


@router.get("/diagnose", status_code=status.HTTP_200_OK)
async def get_diagnose():
    return {"diagnose": True}
