# test_main.py - Автоматизированные тесты на базе Pytest
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app, get_db
from calculator import Layer, MultiLayerStructure, WindowStructure, ThermalCalculator

# Инициализируем тестовый клиент FastAPI
client = TestClient(app)


# --- 1. МОДУЛЬНЫЕ ТЕСТЫ (UNIT TESTS) ---

def test_layer_thermal_resistance():
    """Проверка расчета термического сопротивления отдельного слоя"""
    layer = Layer(thickness=0.12, thermal_conductivity=0.6)
    assert layer.get_thermal_resistance() == pytest.approx(0.2)


def test_multilayer_structure_r0():
    """Проверка расчета полного сопротивления теплопередаче стены (Формула 1)"""
    layer1 = Layer(thickness=0.12, thermal_conductivity=0.6)  # R = 0.2
    layer2 = Layer(thickness=0.05, thermal_conductivity=0.04)  # R = 1.25

    # R0 = 1/8.7 + (0.2 + 1.25) + 1/23 = 0.1149 + 1.45 + 0.0434 = 1.6083
    structure = MultiLayerStructure(
        name="Тестовая стена", area=20.0, orientation="N", layers=[layer1, layer2]
    )
    assert structure.get_r0() == pytest.approx(1.6083, rel=1e-3)


def test_thermal_calculator_winter_load():
    """Проверка вычисления зимней отопительной нагрузки (Формулы 2, 3, 4)"""
    city_mock = {"t_winter_5day": -20.0, "t_summer_max": 30.0}
    calc = ThermalCalculator(
        building_volume=100.0, floor_area=30.0,
        t_inside_winter=20.0, t_inside_summer=24.0, city_data=city_mock
    )

    # Создаем простую конструкцию с фиксированным R0 = 2.0, площадь = 10 м2, ориентация Север (beta=0.1)
    layer = Layer(thickness=0.1, thermal_conductivity=0.05)  # R = 2.0 (для простоты пренебрежем альфа)
    struct = MultiLayerStructure(name="Стена", area=10.0, orientation="N", layers=[layer])
    # Переопределим get_r0 для контролируемого теста
    struct.get_r0 = lambda: 2.0
    calc.add_structure(struct)

    # Ожидаемые потери через конструкции: (10 * 40 / 2.0) * 1.1 = 220 Вт
    # Ожидаемые потери на вентиляцию: 0.28 * 1.005 * 1.2 * 100 * 40 = 1350.72 Вт
    # Бытовые выделения: 10 * 30 = 300 Вт
    # Итог: 220 + 1350.72 - 300 = 1270.72 Вт
    assert calc.calculate_winter_load() == pytest.approx(1270.72, rel=1e-2)


# --- 2. ИНТЕГРАЦИОННЫЕ ТЕСТЫ (INTEGRATION TESTS) ---

def test_calculate_endpoint_validation_error():
    """Проверка валидации Pydantic: отправка некорректных данных (отрицательный объем)"""
    bad_payload = {
        "city_id": 1,
        "building_volume": -50.0,  # Ошибка: должно быть строго больше 0
        "floor_area": 30.0,
        "structures": []
    }
    response = client.post("/api/v1/calculate", json=bad_payload)
    assert response.status_code == 422  # Unprocessable Entity


def test_calculate_endpoint_success_with_mock_db():
    """Сквозной тест эндпоинта с подменой сессии базы данных"""
    # Создаем асинхронный мок для сессии БД
    async_session_mock = AsyncMock()

    # Настраиваем возвращаемые значения из таблиц-справочников БД
    mock_city = MagicMock()
    mock_city.mappings.return_value.first.return_value = {"t_winter_5day": -25.0, "t_summer_max": 32.0}

    mock_material = MagicMock()
    mock_material.mappings.return_value.first.return_value = {"thermal_conductivity": 0.04}

    # При первом вызове (city) возвращаем климат, при втором (material) - теплопроводность
    async_session_mock.execute.side_effect = [mock_city, mock_material]

    # Переопределяем зависимость get_db в FastAPI
    async def override_get_db():
        yield async_session_mock

    app.dependency_overrides[get_db] = override_get_db

    valid_payload = {
        "city_id": 1,
        "building_volume": 120.0,
        "floor_area": 40.0,
        "t_inside_winter": 22.0,
        "t_inside_summer": 24.0,
        "structures": [
            {
                "name": "Наружная стена",
                "type": "wall",
                "area": 25.0,
                "orientation": "S",
                "layers": [{"material_id": 12, "thickness": 0.1}]
            }
        ]
    }

    response = client.post("/api/v1/calculate", json=valid_payload)

    # Сбрасываем переопределение зависимостей
    app.dependency_overrides.clear()

    assert response.status_code == 200
    json_data = response.json()
    assert "q_heating_total_watts" in json_data
    assert "q_cooling_total_watts" in json_data