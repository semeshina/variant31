"""
Backend (REST API) проекта «Учет домашних животных» — вариант 31.

Связывает воедино три компонента:
    Frontend  -> Backend (этот сервис) -> PostgreSQL (внутренняя БД)
    Frontend  -> Backend               -> Web-сервис расчета нормы кормления

Эндпоинты:
    GET  /api/health              — проверка готовности сервиса
    GET  /api/pets                — список карточек питомцев из БД (Кнопка 1)
    GET  /api/pets/<id>/medcard   — медкарта выбранного питомца (Кнопка 1)
    GET  /api/feeding-history     — журнал расчетов нормы кормления из БД
    POST /api/feeding/calculate   — расчет нормы кормления через Web-сервис
                                    с сохранением результата в БД (Кнопка 2)
"""

import os
import time

import psycopg2
import psycopg2.extras
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),
    "port": os.environ.get("DB_PORT", "5432"),
    "dbname": os.environ.get("DB_NAME", "pets_db"),
    "user": os.environ.get("DB_USER", "petuser"),
    "password": os.environ.get("DB_PASSWORD", "petpass"),
}
WEB_SERVICE_URL = os.environ.get("WEB_SERVICE_URL", "http://web-service:5001")

app = Flask(__name__)
CORS(app)


def get_connection(max_attempts: int = 30):
    """Подключение к PostgreSQL с повторными попытками (ожидание БД)."""
    for attempt in range(1, max_attempts + 1):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except psycopg2.OperationalError:
            print(f"[backend] БД недоступна, попытка {attempt}/{max_attempts}...")
            time.sleep(2)
    raise RuntimeError("Не удалось подключиться к PostgreSQL")


def fetch_all(sql: str, params: tuple = ()):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


@app.get("/api/health")
def health():
    try:
        with get_connection(max_attempts=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return jsonify({"status": "ok", "database": "up" if db_ok else "down"}), 200


# ------------------------------------------------------------------
# Кнопка 1: выборка данных из внутренней базы данных
# ------------------------------------------------------------------
@app.get("/api/pets")
def list_pets():
    """Карточки всех питомцев из внутренней БД."""
    rows = fetch_all(
        """
        SELECT id, name, species, breed, sex, weight_kg, age_years,
               birth_date, owner_name
        FROM pets
        ORDER BY id
        """
    )
    for row in rows:
        row["birth_date"] = str(row["birth_date"]) if row["birth_date"] else None
        row["weight_kg"] = float(row["weight_kg"])
        row["age_years"] = float(row["age_years"])
    return jsonify({"pets": rows, "count": len(rows)})


@app.get("/api/pets/<int:pet_id>/medcard")
def medcard(pet_id: int):
    """Медкарта выбранного питомца из внутренней БД."""
    pet = fetch_all("SELECT * FROM pets WHERE id = %s", (pet_id,))
    if not pet:
        return jsonify({"error": "Питомец не найден"}), 404
    visits = fetch_all(
        """
        SELECT id, visit_date, diagnosis, temperature_c, weight_kg, notes
        FROM medcard
        WHERE pet_id = %s
        ORDER BY visit_date DESC
        """,
        (pet_id,),
    )
    pet = pet[0]
    pet["birth_date"] = str(pet["birth_date"]) if pet["birth_date"] else None
    pet["weight_kg"] = float(pet["weight_kg"])
    pet["age_years"] = float(pet["age_years"])
    for v in visits:
        v["visit_date"] = str(v["visit_date"])
        v["temperature_c"] = float(v["temperature_c"]) if v["temperature_c"] is not None else None
        v["weight_kg"] = float(v["weight_kg"]) if v["weight_kg"] is not None else None
    return jsonify({"pet": pet, "visits": visits})


@app.get("/api/feeding-history")
def feeding_history():
    """Журнал расчетов нормы кормления из внутренней БД."""
    rows = fetch_all(
        """
        SELECT h.id, h.pet_id, p.name AS pet_name, h.weight_kg, h.age_years,
               h.daily_kcal, h.daily_food_g, h.meals_per_day, h.advice, h.created_at
        FROM feeding_history h
        JOIN pets p ON p.id = h.pet_id
        ORDER BY h.created_at DESC, h.id DESC
        LIMIT 20
        """
    )
    for row in rows:
        row["weight_kg"] = float(row["weight_kg"])
        row["age_years"] = float(row["age_years"])
        row["daily_kcal"] = float(row["daily_kcal"])
        row["daily_food_g"] = float(row["daily_food_g"])
        row["created_at"] = row["created_at"].strftime("%d.%m.%Y %H:%M")
    return jsonify({"history": rows})


# ------------------------------------------------------------------
# Кнопка 2: запрос к специализированному Web-сервису + запись в БД
# ------------------------------------------------------------------
@app.post("/api/feeding/calculate")
def calculate_feeding():
    """
    Расчет нормы кормления.
    1) Backend запрашивает Web-сервис (по варианту).
    2) Полученный результат сохраняется в таблицу feeding_history (СУБД).
    """
    data = request.get_json(silent=True) or {}

    try:
        pet_id = int(data.get("pet_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Укажите 'pet_id' питомца"}), 400

    pets = fetch_all("SELECT * FROM pets WHERE id = %s", (pet_id,))
    if not pets:
        return jsonify({"error": "Питомец не найден"}), 404
    pet = pets[0]

    # Значения из карточки питомца, но можно переопределить из формы
    weight = float(data.get("weight_kg") or pet["weight_kg"])
    age = float(data.get("age_years") or pet["age_years"])

    try:
        response = requests.post(
            f"{WEB_SERVICE_URL}/api/calculate",
            json={"species": pet["species"], "weight_kg": weight, "age_years": age},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as exc:
        return jsonify({"error": f"Web-сервис недоступен: {exc}"}), 502

    # Сохранение результата во внутреннюю БД
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO feeding_history
                    (pet_id, weight_kg, age_years, daily_kcal, daily_food_g, meals_per_day, advice)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    pet_id,
                    weight,
                    age,
                    result["daily_kcal"],
                    result["daily_food_g"],
                    result["meals_per_day"],
                    result["advice"],
                ),
            )
            history_id = cur.fetchone()[0]
        conn.commit()

    return jsonify({
        "message": f"Расчет для питомца {pet['name']} сохранен в БД (запись #{history_id})",
        "pet": {"id": pet_id, "name": pet["name"], "species": pet["species"]},
        "result": result,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
