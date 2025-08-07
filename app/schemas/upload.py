# app/schemas/upload.py 
# Este código definirá um modelo para a resposta que sua API dará após um upload bem-sucedido.

from pydantic import BaseModel, Field

class UploadResponse(BaseModel):
    """
    Schema for the response after a successful file upload.
    Define a estrutura de dados que será retornada ao cliente.
    """
    filename: str = Field(
        ...,  # O '...' indica que o campo é obrigatório
        example="meu_arquivo.pdf",
        description="O nome original do arquivo que foi enviado."
    )
    content_type: str = Field(
        ...,
        example="application/pdf",
        description="O tipo MIME (Content-Type) do arquivo."
    )
    size_in_bytes: int = Field(
        ...,
        example=102400,
        description="O tamanho do arquivo em bytes."
    )
    message: str = Field(
        "Arquivo recebido com sucesso!",
        description="Uma mensagem de confirmação para o cliente."
    )

    # Configuração para que o Pydantic funcione bem com modelos de ORM
    # e para gerar exemplos na documentação do Swagger/OpenAPI.
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "filename": "relatorio_mensal.xlsx",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "size_in_bytes": 256000,
                "message": "Arquivo recebido com sucesso!"
            }
        }
