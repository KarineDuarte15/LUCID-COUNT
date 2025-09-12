from fastapi import APIRouter
from typing import Dict, List
from app.schemas.tipos import RegimeTributario, TipoDocumento, GRUPOS_POR_REGIME

router = APIRouter(
    prefix="/upload-options",
    tags=["Upload Options"],
)

@router.get("/", response_model=Dict[RegimeTributario, List[TipoDocumento]])
def get_upload_options():
    """
    Retorna a lista de tipos de documentos permitidos para cada regime tributário.
    """
    return GRUPOS_POR_REGIME

@router.get("/regimes", response_model=List[RegimeTributario])
def get_regimes():
    """
    Retorna a lista de todos os regimes tributários disponíveis.
    """
    return list(RegimeTributario)