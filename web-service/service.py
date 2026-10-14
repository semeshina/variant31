"""
Web-сервис (вариант 31): «Учет домашних животных».
Локальный микросервис-эмулятор предметной области:
расчет суточной нормы кормления по весу и возрасту питомца.

Формулы (ветеринарные стандарты):
    RER (покойная энергия)   = 70 * (масса_кг) ** 0.75
    MER (суточная энергия)   = RER * коэффициент_активности (по виду и возрасту)
    Граммов сухого корма/сут = MER / калорийность_корма (3.7 ккал/г)
"""

from flask import Flask, jsonify, request
from math import pow

app = Flask(__name__)

KCAL_PER_GRAM_DRY_FOOD = 3.7  # средняя калорийность сухого корма

# Коэффициенты суточной энергии (MER) по виду и возрастной группе
ACTIVITY_FACTORS = {
    "dog": {"baby": 3.0, "adult": 1.8, "senior": 1.4},
    "cat": {"baby": 2.5, "adult": 1.2, "senior": 1.1},
}

SPECIES_RU = {"dog": "Собака", "cat": "Кошка"}


def age_group(species: str, age_years: float) -> str:
    """Определение возрастной группы питомца."""
    if species == "dog":
        if age_years < 1.0:
            return "baby"
        if age_years < 8.0:
            return "adult"
        return "senior"
    if age_years < 1.0:
        return "baby"
    if age_years < 10.0:
        return "adult"
    return "senior"


def meals_per_day(species: str, group: str) -> int:
    """Рекомендуемое количество кормлений в сутки."""
    if species == "cat":
        return 3 if group != "senior" else 4
    return 3 if group == "baby" else 2


def age_group_ru(group: str) -> str:
    return {"baby": "молодой (щенок/котенок)",
            "adult": "взрослый",
            "senior": "пожилой"}[group]


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "pet-feeding-calculator"})


@app.post("/api/calculate")
def calculate():
    """Расчет суточной нормы кормления по весу и возрасту питомца."""
    data = request.get_json(silent=True) or {}

    species = str(data.get("species", "")).lower()
    if species not in SPECIES_RU:
        return jsonify({"error": "Поле 'species' должно быть 'dog' или 'cat'"}), 400

    try:
        weight = float(data.get("weight_kg"))
        age = float(data.get("age_years"))
    except (TypeError, ValueError):
        return jsonify({"error": "Укажите числовые поля 'weight_kg' и 'age_years'"}), 400

    if weight <= 0 or weight > 200:
        return jsonify({"error": "Вес должен быть в диапазоне от 0 до 200 кг"}), 400
    if age < 0 or age > 30:
        return jsonify({"error": "Возраст должен быть в диапазоне от 0 до 30 лет"}), 400

    group = age_group(species, age)
    factor = ACTIVITY_FACTORS[species][group]
    rer = 70.0 * pow(weight, 0.75)           # покойная энергия, ккал/сут
    mer = rer * factor                        # суточная энергия, ккал/сут
    grams = mer / KCAL_PER_GRAM_DRY_FOOD      # граммов сухого корма в сутки
    meals = meals_per_day(species, group)

    advice = (f"{SPECIES_RU[species]}, возрастная группа: {age_group_ru(group)}. "
              f"Разделите дневную норму ({grams:.0f} г) на {meals} приема(ов) пищи. "
              f"Обязательно обеспечьте постоянный доступ к чистой воде.")

    return jsonify({
        "species": species,
        "species_ru": SPECIES_RU[species],
        "weight_kg": weight,
        "age_years": age,
        "age_group": group,
        "activity_factor": factor,
        "rer_kcal": round(rer, 1),        # RER - энергия в покое
        "daily_kcal": round(mer, 1),      # MER - суточная энергия
        "daily_food_g": round(grams, 1),
        "meals_per_day": meals,
        "advice": advice,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
