import json
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Path as ApiPath, Response
from pydantic import BaseModel, ConfigDict, Field

from common import database
from common.api import create_app, find_or_404

Text = Annotated[str, Field(min_length=1, max_length=150)]
Processo = Literal["natural", "lavado", "honey"]


class Origem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    fazenda: Text
    regiao: Text
    pais: Text


class GraoInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    nome: Text
    origem: Origem
    variedade: Text
    processo: Processo
    ponto_torra: Literal["clara", "média", "escura"]
    notas_sensoriais: list[Text] = Field(min_length=1, max_length=20)
    preco_kg: float = Field(gt=0, le=100000)
    sacas_estoque: int = Field(ge=0, le=1000000)


class Grao(GraoInput):
    id: int


seeds = [GraoInput.model_validate(item).model_dump(mode="json") for item in json.loads(Path(__file__).with_name("seed.json").read_text())]
app = create_app("Grãos", seeds)


@app.get("/graos", response_model=list[Grao])
def listar_graos(regiao: str | None = None, processo: Processo | None = None):
    filters = {}
    if regiao is not None:
        filters["origem"] = {"regiao": regiao}
    if processo is not None:
        filters["processo"] = processo
    return database.list_records(filters)


@app.get("/graos/{id}", response_model=Grao)
def obter_grao(id: Annotated[int, ApiPath(gt=0)]):
    return find_or_404(id)


@app.post("/graos", response_model=Grao, status_code=201)
def criar_grao(payload: GraoInput, response: Response):
    item = database.create_record(payload.model_dump(mode="json"))
    response.headers["Location"] = f"/graos/{item['id']}"
    return item
