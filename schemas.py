from pydantic import BaseModel, Field
from typing import List, Optional

class LayerInput(BaseModel):
    material_id: int = Field(..., description="ID материала из справочника БД")
    thickness: float = Field(..., gt=0, description="Толщина слоя в метрах")

class StructureInput(BaseModel):
    name: str = Field(..., description="Название конструкции (например, Стена Север)")
    type: str = Field(..., description="Тип: wall, roof, floor, window")
    area: float = Field(..., gt=0, description="Площадь в м2")
    orientation: str = Field(..., description="Сторона света: N, S, E, W")
    window_type_id: Optional[int] = Field(None, description="ID окна (только для типа window)")
    layers: List[LayerInput] = Field(default=[], description="Список слоев изнутри наружу")

class CalculationRequest(BaseModel):
    city_id: int = Field(..., description="ID города из справочника климатологии")
    building_volume: float = Field(..., gt=0, description="Внутренний объем здания в м3")
    floor_area: float = Field(..., gt=0, description="Площадь пола в м2 для бытовых выделений")
    t_inside_winter: float = Field(22.0, description="Желаемая температура зимой, °C")
    t_inside_summer: float = Field(24.0, description="Желаемая температура летом, °C")
    structures: List[StructureInput] = Field(..., description="Список всех ограждающих конструкций")

class CalculationResult(BaseModel):
    q_heating_total_watts: float = Field(..., description="Итоговая нагрузка на отопление (зима), Вт")
    q_cooling_total_watts: float = Field(..., description="Итоговая нагрузка на кондиционирование (лето), Вт")