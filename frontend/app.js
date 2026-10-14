/* Фронтенд «Учет домашних животных» — вариант 31.
   Все запросы идут на /api — Nginx проксирует их в backend. */

const $ = (id) => document.getElementById(id);

let petsCache = [];

/* ---------- Кнопка 1: данные из внутренней БД ---------- */
$("loadPetsBtn").addEventListener("click", loadPets);

async function loadPets() {
    try {
        const res = await fetch("/api/pets");
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        petsCache = data.pets || [];
        renderPets(petsCache);
        fillPetSelect(petsCache);
    } catch (err) {
        $("petsTable").innerHTML = `<p class="error">Ошибка загрузки: ${err.message}</p>`;
    }
}

const SPECIES_RU = { dog: "🐶 Собака", cat: "🐱 Кошка" };

function renderPets(pets) {
    if (!pets.length) {
        $("petsTable").innerHTML = '<p class="muted">В базе нет записей о питомцах.</p>';
        return;
    }
    const rows = pets.map(p => `
        <tr>
            <td>${p.id}</td>
            <td><strong>${p.name}</strong></td>
            <td>${SPECIES_RU[p.species] || p.species}</td>
            <td>${p.breed || "—"}</td>
            <td>${p.weight_kg} кг</td>
            <td>${p.age_years} лет</td>
            <td><button class="btn small" data-id="${p.id}">Медкарта</button></td>
        </tr>`).join("");
    $("petsTable").innerHTML = `
        <table>
            <thead><tr>
                <th>ID</th><th>Кличка</th><th>Вид</th><th>Порода</th>
                <th>Вес</th><th>Возраст</th><th></th>
            </tr></thead>
            <tbody>${rows}</tbody>
        </table>`;
    document.querySelectorAll("button[data-id]").forEach(btn =>
        btn.addEventListener("click", () => loadMedcard(btn.dataset.id)));
}

/* ---------- Медкарта питомца (тоже данные из БД) ---------- */
async function loadMedcard(petId) {
    try {
        const res = await fetch(`/api/pets/${petId}/medcard`);
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        const pet = data.pet;
        const visits = data.visits || [];
        const visitRows = visits.map(v => `
            <tr>
                <td>${v.visit_date}</td>
                <td>${v.diagnosis || "—"}</td>
                <td>${v.temperature_c ?? "—"} °C</td>
                <td>${v.weight_kg ?? "—"} кг</td>
                <td>${v.notes || "—"}</td>
            </tr>`).join("");
        $("medcardBox").innerHTML = `
            <p><strong>${pet.name}</strong> · ${SPECIES_RU[pet.species] || pet.species}
               · ${pet.breed || "порода не указана"} · владелец: ${pet.owner_name || "—"}
               · дата рождения: ${pet.birth_date || "—"} · вес: ${pet.weight_kg} кг · возраст: ${pet.age_years} лет</p>
            <table>
                <thead><tr>
                    <th>Дата визита</th><th>Диагноз</th><th>Температура</th><th>Вес</th><th>Примечания</th>
                </tr></thead>
                <tbody>${visitRows || '<tr><td colspan="5">Записей нет</td></tr>'}</tbody>
            </table>`;
    } catch (err) {
        $("medcardBox").innerHTML = `<p class="error">Ошибка загрузки медкарты: ${err.message}</p>`;
    }
}

function fillPetSelect(pets) {
    $("petSelect").innerHTML =
        '<option value="">— выберите питомца —</option>' +
        pets.map(p => `<option value="${p.id}">${p.name} (${SPECIES_RU[p.species] || p.species})</option>`).join("");
}

/* ---------- Кнопка 2: запрос к специализированному Web-сервису ---------- */
$("calcBtn").addEventListener("click", calculateFeeding);

async function calculateFeeding() {
    const petId = $("petSelect").value;
    if (!petId) {
        $("resultBox").innerHTML = '<p class="error">Сначала загрузите список питомцев и выберите одного.</p>';
        return;
    }
    const payload = { pet_id: parseInt(petId, 10) };
    if ($("weightInput").value) payload.weight_kg = parseFloat($("weightInput").value);
    if ($("ageInput").value) payload.age_years = parseFloat($("ageInput").value);

    try {
        const res = await fetch("/api/feeding/calculate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "HTTP " + res.status);
        renderResult(data);
        loadHistory();
    } catch (err) {
        $("resultBox").innerHTML = `<p class="error">Ошибка расчета: ${err.message}</p>`;
    }
}

function renderResult(data) {
    const r = data.result;
    $("resultBox").innerHTML = `
        <div class="result-grid">
            <div class="result-item"><div class="value">${r.daily_food_g} г</div><div class="label">Суточная норма корма</div></div>
            <div class="result-item"><div class="value">${r.daily_kcal} ккал</div><div class="label">Суточная энергия (MER)</div></div>
            <div class="result-item"><div class="value">${r.rer_kcal} ккал</div><div class="label">Энергия в покое (RER)</div></div>
            <div class="result-item"><div class="value">${r.meals_per_day}× в день</div><div class="label">Количество кормлений</div></div>
        </div>
        <div class="advice">✔ ${data.message}<br>${r.advice}</div>`;
}

/* ---------- История расчетов из БД ---------- */
$("loadHistoryBtn").addEventListener("click", loadHistory);

async function loadHistory() {
    try {
        const res = await fetch("/api/feeding-history");
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        const history = data.history || [];
        if (!history.length) {
            $("historyTable").innerHTML = '<p class="muted">Расчетов еще не было.</p>';
            return;
        }
        const rows = history.map(h => `
            <tr>
                <td>${h.created_at}</td>
                <td>${h.pet_name}</td>
                <td>${h.weight_kg} кг</td>
                <td>${h.age_years} лет</td>
                <td>${h.daily_food_g} г</td>
                <td>${h.daily_kcal} ккал</td>
                <td>${h.meals_per_day}×</td>
            </tr>`).join("");
        $("historyTable").innerHTML = `
            <table>
                <thead><tr>
                    <th>Дата</th><th>Питомец</th><th>Вес</th><th>Возраст</th>
                    <th>Норма корма</th><th>Энергия</th><th>Кормлений</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>`;
    } catch (err) {
        $("historyTable").innerHTML = `<p class="error">Ошибка загрузки истории: ${err.message}</p>`;
    }
}

/* ---------- Первоначальная загрузка ---------- */
loadHistory();
