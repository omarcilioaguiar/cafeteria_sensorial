import json
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Path as ApiPath, Response
from pydantic import BaseModel, ConfigDict, Field

from common import database
from common.api import create_app, find_or_404

Moagem = Literal["fina", "média", "grossa"]


class MetodoInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    nome: str = Field(min_length=1, max_length=100)
    proporcao: str = Field(pattern=r"^1:[1-9][0-9]*(\.[0-9]+)?$", description="Café:água em massa, por exemplo 1:15")
    moagem: Moagem
    temperatura_c: float = Field(gt=0, le=100)
    tempo_segundos: int = Field(gt=0, le=86400)


class Metodo(MetodoInput):
    id: int


seeds = [MetodoInput.model_validate(item).model_dump(mode="json") for item in json.loads(Path(__file__).with_name("seed.json").read_text())]
app = create_app("Métodos", seeds)


@app.get("/metodos", response_model=list[Metodo])
def listar_metodos(moagem: Moagem | None = None):
    return database.list_records({"moagem": moagem} if moagem is not None else {})


@app.get("/metodos/{id}", response_model=Metodo)
def obter_metodo(id: Annotated[int, ApiPath(gt=0)]):
    return find_or_404(id)


@app.post("/metodos", response_model=Metodo, status_code=201)
def criar_metodo(payload: MetodoInput, response: Response):
    item = database.create_record(payload.model_dump(mode="json"))
    response.headers["Location"] = f"/metodos/{item['id']}"
    return item
