from fastapi import APIRouter, status
from incidentbot.diagnostics.BedRockHandler import BedRockHandler

router = APIRouter()


@router.get("/diagnose", status_code=status.HTTP_200_OK)
async def get_diagnose():
    print("get_diagnose is being called.")
    
    agent_response: str = BedRockHandler.invoke_bedrock_agent(
        agent_id="MH00AZX5TB",
        agent_alias_id="GIITVBBSUU",
        input_text="Hello, I'm Deep Purple. How are you today?",
        enable_trace=True, 
        end_session=False
    )

    return {"diagnose": agent_response}
