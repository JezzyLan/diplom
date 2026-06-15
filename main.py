# main.py - Главный модуль веб-приложения FastAPI
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict

# Импортируем наши локальные модули
from schemas import CalculationRequest, CalculationResult
from calculator import Layer, MultiLayerStructure, WindowStructure, ThermalCalculator
from database import get_db  # <--- Импортируем подключение из нового файла
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="API Системы автоматизированного расчета")

templates = Jinja2Templates(directory="templates")

# Разрешаем запросы с любых доменов (CORS) для демонстрации
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В рабочей среде здесь указывают домен фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Карта интенсивности солнечной радиации (нормативные константы)
SOLAR_INTENSITY: Dict[str, float] = {"N": 95.0, "S": 210.0, "E": 175.0, "W": 175.0}

@app.post("/api/v1/calculate", response_model=CalculationResult, status_code=status.HTTP_200_OK)
async def process_thermal_calculation(request: CalculationRequest, db: AsyncSession = Depends(get_db)):
    # 1. Извлечение климатических данных из БД
    city_query = await db.execute(
        text("SELECT t_winter_5day, t_summer_max FROM climatology WHERE id = :id"),
        {"id": request.city_id}
    )
    city = city_query.mappings().first()
    if not city:
        raise HTTPException(status_code=404, detail="Указанный город не найден в базе данных")

    # 2. Инициализация главного ООП-контроллера расчета здания
    calculator = ThermalCalculator(
        building_volume=request.building_volume,
        floor_area=request.floor_area,
        t_inside_winter=request.t_inside_winter,
        t_inside_summer=request.t_inside_summer,
        city_data=city
    )

    # 3. Сборка объектов конструкций здания из данных запроса и справочников БД
    for struct in request.structures:
        if struct.type == "window":
            if not struct.window_type_id:
                raise HTTPException(status_code=400, detail=f"Для окна '{struct.name}' не указан window_type_id")

            win_query = await db.execute(
                text("SELECT r_value, solar_factor FROM window_types WHERE id = :id"),
                {"id": struct.window_type_id}
            )
            win_data = win_query.mappings().first()
            if not win_data:
                raise HTTPException(status_code=404, detail="Тип стеклопакета не найден")

            # Создание объекта светопрозрачной конструкции
            window_obj = WindowStructure(
                name=struct.name, area=struct.area, orientation=struct.orientation,
                r_value=float(win_data['r_value']), solar_factor=float(win_data['solar_factor'])
            )
            calculator.add_structure(window_obj)

        else:
            # Сборка многослойной конструкции (стена, крыша, пол)
            object_layers = []
            for layer in struct.layers:
                mat_query = await db.execute(
                    text("SELECT thermal_conductivity FROM materials WHERE id = :id"),
                    {"id": layer.material_id}
                )
                mat_data = mat_query.mappings().first()
                if not mat_data:
                    raise HTTPException(status_code=404, detail=f"Материал с id {layer.material_id} не найден")

                # Инициализация объекта физического слоя
                object_layers.append(
                    Layer(thickness=layer.thickness, thermal_conductivity=float(mat_data['thermal_conductivity']))
                )

            if not object_layers:
                raise HTTPException(status_code=400, detail=f"Конструкция '{struct.name}' должна содержать слои")

            # Создание объекта многослойной конструкции
            structure_obj = MultiLayerStructure(
                name=struct.name, area=struct.area, orientation=struct.orientation, layers=object_layers
            )
            calculator.add_structure(structure_obj)

    # 4. Полиморфный запуск расчета и формирование валидного ответа
    return CalculationResult(
        q_heating_total_watts=calculator.calculate_winter_load(),
        q_cooling_total_watts=calculator.calculate_summer_load(SOLAR_INTENSITY)
    )


@app.get("/api/v1/regions")
async def get_regions(db: AsyncSession = Depends(get_db)):
    """Эндпоинт для получения списка городов из БД для фронтенда"""
    result = await db.execute(text("SELECT id, city_name AS name FROM climatology ORDER BY city_name"))
    return result.mappings().all()


@app.get('/')
async def get_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="app.html"
    )