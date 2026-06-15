from abc import ABC, abstractmethod
from typing import List, Dict


class Layer:
    """Класс, представляющий отдельный физический слой конструкции"""

    def __init__(self, thickness: float, thermal_conductivity: float):
        self.thickness = thickness
        self.thermal_conductivity = thermal_conductivity

    def get_thermal_resistance(self) -> float:
        """Возвращает термическое сопротивление слоя"""
        return self.thickness / self.thermal_conductivity


class BuildingStructure(ABC):
    """Абстрактный базовый класс для всех типов ограждающих конструкций"""

    def __init__(self, name: str, area: float, orientation: str):
        self.name = name
        self.area = area
        self.orientation = orientation

    @abstractmethod
    def get_r0(self) -> float:
        """Абстрактный метод для получения полного сопротивления теплопередаче"""
        pass


class MultiLayerStructure(BuildingStructure):
    """Класс многослойной конструкции (стены, кровли, перекрытия)"""

    def __init__(self, name: str, area: float, orientation: str, layers: List[Layer],
                 alpha_v_n: float = 8.7, alpha_n: float = 23.0):
        super().__init__(name, area, orientation)
        self.layers = layers
        self.alpha_v_n = alpha_v_n
        self.alpha_n = alpha_n

    def get_r0(self) -> float:
        """Расчет общего сопротивления теплопередаче многослойной стены (Формула 1)"""
        layers_resistance = sum(layer.get_thermal_resistance() for layer in self.layers)
        return (1 / self.alpha_v_n) + layers_resistance + (1 / self.alpha_n)


class WindowStructure(BuildingStructure):
    """Класс светопрозрачной конструкции (окна, витражи)"""

    def __init__(self, name: str, area: float, orientation: str, r_value: float, solar_factor: float):
        super().__init__(name, area, orientation)
        self.r_value = r_value
        self.solar_factor = solar_factor

    def get_r0(self) -> float:
        """Возвращает готовое сопротивление окна из паспорта изделия / справочника"""
        return self.r_value


class ThermalCalculator:
    """Управляющий класс-контроллер теплотехнических вычислений здания"""

    def __init__(self, building_volume: float, floor_area: float,
                 t_inside_winter: float, t_inside_summer: float, city_data: dict):
        self.volume = building_volume
        self.floor_area = floor_area
        self.t_winter = t_inside_winter
        self.t_summer = t_inside_summer
        self.city = city_data
        self.structures: List[BuildingStructure] = []

    def add_structure(self, structure: BuildingStructure):
        """Полиморфное добавление конструкции в объект здания"""
        self.structures.append(structure)

    def calculate_winter_load(self) -> float:
        """Расчет пиковой нагрузки на систему отопления"""
        delta_t = self.t_winter - float(self.city['t_winter_5day'])

        q_zim_ogr = 0.0
        for struct in self.structures:
            beta = 0.1 if struct.orientation in ['N', 'E', 'W'] else 0.0
            q_zim_ogr += (struct.area * delta_t / struct.get_r0()) * (1 + beta)

        air_flow = self.volume * 1.0  # Кратность воздухообмена = 1
        q_zim_vent = 0.28 * 1.005 * 1.2 * air_flow * delta_t
        q_byt = 10.0 * self.floor_area

        return max(0.0, q_zim_ogr + q_zim_vent - q_byt)

    def calculate_summer_load(self, solar_intensity: Dict[str, float]) -> float:
        """Расчет пиковой нагрузки на систему кондиционирования"""
        delta_t = float(self.city['t_summer_max']) - self.t_summer

        q_let_ogr = 0.0
        q_soln = 0.0

        for struct in self.structures:
            if isinstance(struct, WindowStructure):
                intensity = solar_intensity.get(struct.orientation, 150.0)
                q_soln += struct.area * intensity * struct.solar_factor
            else:
                q_let_ogr += (struct.area * delta_t / struct.get_r0())

        air_flow = self.volume * 1.0
        q_let_vent = 0.28 * 1.005 * 1.2 * air_flow * delta_t
        q_byt = 10.0 * self.floor_area

        return q_let_ogr + q_soln + q_let_vent + q_byt
    