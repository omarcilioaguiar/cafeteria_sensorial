import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Path as ApiPath, Query, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from common import database
from common.api import create_app, find_or_404


class Parametros(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    moagem: Literal["fina", "média", "grossa"]
    temperatura_c: float = Field(gt=0, le=100)
    tempo_segundos: int = Field(gt=0, le=86400)


class Avaliacao(BaseModel):
    model_config = ConfigDict(extra="forbid")
    acidez: int = Field(ge=1, le=5)
    corpo: int = Field(ge=1, le=5)
    docura: int = Field(ge=1, le=5)


class DegustacaoInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    grao_id: int = Field(gt=0)
    metodo_id: int = Field(gt=0)
    parametros: Parametros
    avaliacao: Avaliacao
    nota_final: float = Field(ge=0, le=10, description="Nota geral do barista, de 0 a 10")
    comentario: str = Field(max_length=2000)
    data: AwareDatetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Degustacao(DegustacaoInput):
    id: int


seeds = [DegustacaoInput.model_validate(item).model_dump(mode="json") for item in json.loads(Path(__file__).with_name("seed.json").read_text())]
app = create_app("Degustações", seeds)


@app.get("/degustacoes", response_model=list[Degustacao])
def listar_degustacoes(grao_id: Annotated[int | None, Query(gt=0)] = None):
    return database.list_records({"grao_id": grao_id} if grao_id is not None else {})


@app.get("/degustacoes/{id}", response_model=Degustacao)
def obter_degustacao(id: Annotated[int, ApiPath(gt=0)]):
    return find_or_404(id)


@app.get("/graos/{id}/degustacoes", response_model=list[Degustacao])
def degustacoes_por_grao(id: Annotated[int, ApiPath(gt=0)]):
    return database.list_records({"grao_id": id})


@app.post("/degustacoes", response_model=Degustacao, status_code=201)
def criar_degustacao(payload: DegustacaoInput, response: Response):
    item = database.create_record(payload.model_dump(mode="json"))
    response.headers["Location"] = f"/degustacoes/{item['id']}"
    return item
