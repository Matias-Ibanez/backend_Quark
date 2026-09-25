from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Element(Strict):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[\w-]+$")
    type: Literal["text", "image", "shape"] = "text"
    text: str = Field(default="", max_length=600)
    assetId: str | None = None
    x: float = Field(default=8, ge=0, le=100)
    y: float = Field(default=8, ge=0, le=100)
    width: float = Field(default=84, ge=1, le=100)
    height: float = Field(default=18, ge=1, le=100)
    fontSize: int = Field(default=72, ge=12, le=220)
    color: str = Field(default="#20251f", pattern=r"^#[0-9a-fA-F]{6}$")
    weight: Literal["400", "600", "800"] = "800"
    align: Literal["left", "center", "right"] = "left"
    fit: Literal["contain", "cover"] = "contain"
    radius: int = Field(default=0, ge=0, le=300)
    opacity: float = Field(default=1, ge=0, le=1)
    animation: Literal["none", "fade", "rise", "zoom"] = "fade"


class Scene(Strict):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[\w-]+$")
    name: str = Field(default="Escena", min_length=1, max_length=100)
    duration: float = Field(default=5, ge=1, le=60)
    background: str = Field(default="#eeeae1", pattern=r"^#[0-9a-fA-F]{6}$")
    elements: list[Element] = Field(default_factory=list, max_length=30)


class Document(Strict):
    format: Literal["portrait", "square", "story"] = "portrait"
    engine: Literal["remotion", "manim"] = "remotion"
    fps: Literal[24, 30] = 24
    scenes: list[Scene] = Field(min_length=1, max_length=20)
    audioAssetId: str | None = None
    caption: str = Field(default="", max_length=2200)

    @model_validator(mode="after")
    def check_scene_ids(self):
        if sum(s.duration for s in self.scenes) > 180:
            raise ValueError("El prototipo admite hasta 180 segundos por video")
        ids = [s.id for s in self.scenes]
        if len(ids) != len(set(ids)):
            raise ValueError("Los identificadores de escena deben ser únicos")
        for scene in self.scenes:
            ids = [e.id for e in scene.elements]
            if len(ids) != len(set(ids)):
                raise ValueError("Los identificadores de elementos deben ser únicos por escena")
        return self


def initial_document():
    return Document(scenes=[Scene(id="scene-1", name="Presentación", elements=[
        Element(id="brand", text="TU MARCA", fontSize=26, y=7, height=6, weight="600"),
        Element(id="title", text="Una nueva\nforma de crear.", y=18, height=26, fontSize=96),
        Element(id="description", text="Sumá tu producto y hacé propia esta composición.", y=48, height=14, fontSize=36, weight="400"),
        Element(id="accent", type="shape", y=72, width=84, height=1, color="#c0d9a8"),
        Element(id="cta", text="DESCUBRÍ LA COLECCIÓN", y=82, height=7, fontSize=28, weight="600"),
    ])]).model_dump()


class CreateProject(Strict):
    name: str = Field(min_length=1, max_length=100)
    templateId: str | None = None


class EditProject(Strict):
    revision: int = Field(ge=1)
    document: Document
    label: str = Field(default="Edición manual", max_length=120)
    name: str | None = Field(default=None, min_length=1, max_length=100)


class Crop(Strict):
    left: float = Field(ge=0, lt=1)
    top: float = Field(ge=0, lt=1)
    right: float = Field(gt=0, le=1)
    bottom: float = Field(gt=0, le=1)


class Brand(Strict):
    name: str = Field(default="Mi marca", max_length=100)
    tone: str = Field(default="Cercano, claro y directo", max_length=500)
    context: str = Field(default="", max_length=16000)


class Chat(Strict):
    message: str = Field(min_length=1, max_length=6000)
    function: Literal["content", "strategy", "calendar", "promo", "shorts"] = "content"
    assetIds: list[str] = Field(default_factory=list, max_length=5)
