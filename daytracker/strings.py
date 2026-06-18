"""All user-facing strings, in Romanian.

Kept in one place so the bot's voice stays consistent and easy to edit.
Messages use Telegram HTML formatting (the bot's default parse mode).
"""

from __future__ import annotations

import html
import random
from datetime import date
from typing import TYPE_CHECKING

from .targets import Activity, Goal, Sex

if TYPE_CHECKING:
    from .estimator import MealEstimate
    from .models import ActivityLog, Meal, Profile, WeightLog
    from .repository import DayStat, DaySummary, DayTotals, LastEntry, WeekSummary


def _esc(text: str) -> str:
    """Escape user-supplied text for Telegram HTML (the bot's parse mode)."""
    return html.escape(text or "", quote=False)


START = (
    "👋 <b>Salut!</b> Sunt botul tău pentru urmărirea meselor și a activității zilnice.\n\n"
    "Te ajut să ții evidența caloriilor și a macronutrienților (proteine, carbohidrați, "
    "grăsimi), cu ținte personalizate și rezumate zilnice.\n\n"
    "Scrie /ajutor ca să vezi toate comenzile."
)

HELP = (
    "📋 <b>Comenzi</b>\n\n"
    "/start – pornește botul și vezi mesajul de bun venit\n"
    "/profil – completează-ți profilul (sex, vârstă, înălțime, greutate, obiectiv)\n"
    "/tinte – vezi și ajustează țintele zilnice de calorii și macronutrienți\n"
    "/masa – înregistrează o masă, ex: <code>/masa 100g piept de pui, 40g orez</code>\n"
    "/activitate – înregistrează activitate fizică, ex: <code>/activitate 30 min alergare</code>\n"
    "/apa – înregistrează apa băută în ml, ex: <code>/apa 500</code>\n"
    "/cantar – înregistrează greutatea în kg, ex: <code>/cantar 64.5</code>\n"
    "/azi – vezi rezumatul de azi (mese, activitate, apă, totaluri)\n"
    "/sterge – șterge ultima înregistrare\n"
    "/sumar – rezumatul zilei\n"
    "/saptamana – raportul săptămânal\n"
    "/ajutor – afișează acest mesaj\n\n"
    "💡 Comenzile /masa și /activitate funcționează și ca descriere (caption) la o poză."
)

# Last-resort message when an unexpected error escapes a handler (P7). Calm and
# non-technical — she can simply try again.
GENERIC_ERROR = "Hopa, ceva n-a mers de partea mea. 😅 Mai încearcă o dată peste un moment."

# --- Profil & ținte (P2) -------------------------------------------------------

# Short labels for displaying a saved choice back to the user.
SEX_LABELS = {Sex.FEMALE: "Femeie", Sex.MALE: "Bărbat"}
GOAL_LABELS = {Goal.LOSE: "Slăbire", Goal.MAINTAIN: "Menținere", Goal.GAIN: "Creștere"}
ACTIVITY_LABELS = {
    Activity.SEDENTARY: "Sedentar",
    Activity.LIGHT: "Ușor activ",
    Activity.MODERATE: "Moderat activ",
    Activity.ACTIVE: "Foarte activ",
    Activity.VERY_ACTIVE: "Extrem de activ",
}

# Keyboard button captions (more descriptive than the short labels above). The
# handler maps the tapped caption back to the enum, so these must stay unique.
SEX_BUTTONS = {Sex.FEMALE: "Femeie", Sex.MALE: "Bărbat"}
GOAL_BUTTONS = {
    Goal.LOSE: "📉 Slăbesc",
    Goal.MAINTAIN: "⚖️ Mențin greutatea",
    Goal.GAIN: "📈 Pun masă",
}
ACTIVITY_BUTTONS = {
    Activity.SEDENTARY: "Sedentar (birou, fără sport)",
    Activity.LIGHT: "Ușor activ (1–3 antrenamente/săpt)",
    Activity.MODERATE: "Moderat activ (3–5 antrenamente/săpt)",
    Activity.ACTIVE: "Foarte activ (6–7 antrenamente/săpt)",
    Activity.VERY_ACTIVE: "Extrem de activ (muncă fizică + sport)",
}

PROFIL_START = (
    "📝 <b>Hai să-ți completăm profilul.</b>\n"
    "Pe baza lui calculez țintele zilnice de calorii și macronutrienți.\n"
    "Poți scrie /renunta oricând ca să te oprești.\n\n"
    "Pentru început, care e sexul tău?"
)
PROFIL_ASK_AGE = "Câți ani ai?"
PROFIL_ASK_HEIGHT = "Ce înălțime ai, în cm? (ex: <code>168</code>)"
PROFIL_ASK_WEIGHT = "Ce greutate ai, în kg? (ex: <code>64,5</code>)"
PROFIL_ASK_ACTIVITY = "Cât de activă ești de obicei?"
PROFIL_ASK_GOAL = "Care e obiectivul tău?"

PROFIL_PICK_BUTTON = "Te rog alege una dintre opțiunile de mai jos. 🙂"
PROFIL_CANCELLED = "Am anulat completarea profilului. Scrie /profil când vrei să reluăm."

ERR_AGE = "Vârsta trebuie să fie un număr întreg între 10 și 100. Mai încearcă o dată."
ERR_HEIGHT = "Înălțimea trebuie să fie un număr între 100 și 250 cm. Mai încearcă o dată."
ERR_WEIGHT = "Greutatea trebuie să fie un număr între 30 și 300 kg. Mai încearcă o dată."

TINTE_NO_PROFILE = "Nu am încă profilul tău. Scrie /profil ca să-l completăm întâi."
TINTE_HINT = (
    "💡 Ca să ajustezi caloriile, scrie de ex. <code>/tinte 1600</code>. "
    "Restul macronutrienților se recalculează automat."
)
ERR_TINTE_KCAL = (
    "Scrie un număr întreg de calorii între 800 și 6000, de ex. <code>/tinte 1600</code>."
)


def _fmt_num(value: float) -> str:
    """Trim trailing zeros and use a Romanian decimal comma (64.5 → '64,5')."""
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def format_targets_block(profile: Profile) -> str:
    """The daily kcal + macro targets, as a reusable block."""
    lines = [
        "🎯 <b>Ținte zilnice</b>",
        f"🔥 Calorii: <b>{profile.target_kcal}</b> kcal",
        f"🥩 Proteine: <b>{profile.target_protein_g}</b> g",
        f"🍞 Carbohidrați: <b>{profile.target_carbs_g}</b> g",
        f"🥑 Grăsimi: <b>{profile.target_fat_g}</b> g",
    ]
    if profile.manual_kcal is not None:
        lines.append("✏️ <i>Calorii ajustate manual</i>")
    return "\n".join(lines)


def format_profile_summary(profile: Profile) -> str:
    """Profile inputs followed by the computed targets."""
    sex = SEX_LABELS.get(profile.sex, profile.sex)
    activity = ACTIVITY_LABELS.get(profile.activity, profile.activity)
    goal = GOAL_LABELS.get(profile.goal, profile.goal)
    return (
        "👤 <b>Profilul tău</b>\n"
        f"Sex: {sex} · Vârstă: {profile.age} ani\n"
        f"Înălțime: {_fmt_num(profile.height_cm)} cm · "
        f"Greutate: {_fmt_num(profile.weight_kg)} kg\n"
        f"Activitate: {activity} · Obiectiv: {goal}\n\n"
        f"{format_targets_block(profile)}"
    )


def format_profile_saved(profile: Profile) -> str:
    """Confirmation shown when /profil completes."""
    return (
        "✅ <b>Gata! Profil salvat.</b>\n\n"
        f"{format_profile_summary(profile)}\n\n"
        f"{TINTE_HINT}"
    )


def format_targets_view(profile: Profile, computed_kcal: int | None = None) -> str:
    """Targets shown by /tinte; notes the profile-computed baseline if overridden."""
    text = format_targets_block(profile)
    if profile.manual_kcal is not None and computed_kcal is not None:
        text += (
            f"\n\nℹ️ Valoarea calculată din profil este <b>{computed_kcal}</b> kcal. "
            "Refă /profil ca să revii la ea."
        )
    return f"{text}\n\n{TINTE_HINT}"


def format_targets_updated(profile: Profile) -> str:
    """Confirmation shown after /tinte changes the kcal target."""
    return f"✅ <b>Calorii actualizate.</b>\n\n{format_targets_block(profile)}"


# --- Masă / mese (P3) ----------------------------------------------------------

MASA_EMPTY = (
    "Scrie ce ai mâncat după comandă, de ex. "
    "<code>/masa 100g piept de pui, 40g orez</code>.\n"
    "Poți trimite comanda și ca descriere (caption) la o poză."
)
MASA_UNPARSEABLE = (
    "Nu am recunoscut niciun aliment în text. 🤔\n"
    "Încearcă să descrii mâncarea, de ex. "
    "<code>/masa 2 ouă și o felie de pâine</code>."
)
MASA_LLM_ERROR = (
    "Nu am putut estima macronutrienții acum (serviciul AI nu a răspuns). "
    "Mai încearcă o dată peste câteva momente. 🙏"
)
MASA_TOO_LONG = (
    "Descrierea mesei e prea lungă. ✂️ Scrie mai pe scurt ce ai mâncat "
    "(de ex. <code>/masa 100g piept de pui, 40g orez</code>)."
)


def _macros_inline(protein_g: int, carbs_g: int, fat_g: int) -> str:
    """Compact macro triple used on item and total lines."""
    return f"{protein_g}P / {carbs_g}C / {fat_g}G"


def _format_item_line(name: str, grams: float | None, kcal: int, macros: str) -> str:
    safe_name = _esc(name)  # item names come from the LLM — escape for Telegram HTML
    head = f"{safe_name} ({_fmt_num(grams)} g)" if grams is not None else safe_name
    return f"• {head}: <b>{kcal}</b> kcal · {macros}"


def _format_day_progress(day: DayTotals, profile: Profile | None) -> str:
    """Running daily totals, shown against targets when a profile exists."""
    if profile is None:
        return (
            f"📊 <b>Azi:</b> {day.kcal} kcal · "
            f"{_macros_inline(day.protein_g, day.carbs_g, day.fat_g)}\n"
            "💡 Scrie /profil ca să-ți calculez ținte zilnice."
        )
    pct = round(day.kcal / profile.target_kcal * 100) if profile.target_kcal else 0
    return (
        f"📊 <b>Azi:</b> {day.kcal}/{profile.target_kcal} kcal ({pct}%)\n"
        f"🥩 {day.protein_g}/{profile.target_protein_g} g · "
        f"🍞 {day.carbs_g}/{profile.target_carbs_g} g · "
        f"🥑 {day.fat_g}/{profile.target_fat_g} g"
    )


def format_meal_logged(estimate: MealEstimate, day: DayTotals, profile: Profile | None) -> str:
    """Reply after a meal is logged: items, meal total, and the running daily total."""
    lines = ["🍽️ <b>Masă înregistrată</b>"]
    for item in estimate.items:
        lines.append(
            _format_item_line(
                item.name,
                item.grams,
                item.kcal,
                _macros_inline(item.protein_g, item.carbs_g, item.fat_g),
            )
        )
    lines.append("")
    lines.append(
        f"<b>Total masă:</b> {estimate.kcal} kcal · "
        f"{_macros_inline(estimate.protein_g, estimate.carbs_g, estimate.fat_g)}"
    )
    if estimate.approximate:
        lines.append("⚠️ <i>Estimare aproximativă (porții presupuse).</i>")
    if estimate.note:
        lines.append(f"ℹ️ <i>{_esc(estimate.note)}</i>")
    lines.append("")
    lines.append(_format_day_progress(day, profile))
    return "\n".join(lines)


# --- Activitate / apă / cântar / azi / șterge (P4) -----------------------------

ACTIVITATE_EMPTY = (
    "Scrie ce activitate ai făcut după comandă, de ex. "
    "<code>/activitate 30 min alergare</code>.\n"
    "Poți trimite comanda și ca descriere (caption) la o poză."
)
ACTIVITATE_TOO_LONG = (
    "Descrierea activității e prea lungă. ✂️ Scrie mai pe scurt "
    "(de ex. <code>/activitate 30 min alergare</code>)."
)
ERR_APA = (
    "Scrie câți ml de apă ai băut, de ex. <code>/apa 500</code> " "(număr întreg între 1 și 5000)."
)
ERR_CANTAR = "Scrie greutatea în kg, de ex. <code>/cantar 64,5</code> " "(număr între 30 și 300)."

STERGE_NOTHING = "Nu am găsit nicio înregistrare de șters. 🤔"
STERGE_CANCELLED = "Am anulat. Nu am șters nimic."

# Reply-keyboard captions for the /sterge confirmation (no inline callbacks).
STERGE_YES = "✅ Da, șterge"
STERGE_NO = "❌ Nu, păstrează"


def format_activity_logged(text: str) -> str:
    return f"🏃 <b>Activitate înregistrată.</b>\n{_esc(text)}"


def format_water_logged(added_ml: int, total_ml: int) -> str:
    return f"💧 <b>Apă înregistrată:</b> +{added_ml} ml\n" f"Total azi: <b>{total_ml}</b> ml"


def format_weight_logged(weight_kg: float) -> str:
    return f"⚖️ <b>Greutate înregistrată:</b> {_fmt_num(weight_kg)} kg"


def format_today(
    log_date: date,
    meals: list[Meal],
    day: DayTotals,
    activities: list[ActivityLog],
    water_ml: int,
    weight: WeightLog | None,
    profile: Profile | None,
) -> str:
    """The /azi view: today's meals + totals vs targets, activity, water, weight."""
    lines = [f"📅 <b>Azi</b> ({log_date.strftime('%d.%m.%Y')})", ""]

    lines.append("🍽️ <b>Mese</b>")
    if meals:
        for meal in meals:
            lines.append(f"• {_esc(meal.raw_text)} — <b>{meal.total_kcal}</b> kcal")
    else:
        lines.append("<i>nimic încă</i>")
    lines.append("")
    lines.append(_format_day_progress(day, profile))
    lines.append("")

    lines.append("🏃 <b>Activitate</b>")
    if activities:
        for activity in activities:
            lines.append(f"• {_esc(activity.raw_text)}")
    else:
        lines.append("<i>nimic</i>")
    lines.append("")

    lines.append(f"💧 <b>Apă:</b> {water_ml} ml")
    weight_text = f"{_fmt_num(weight.weight_kg)} kg" if weight is not None else "—"
    lines.append(f"⚖️ <b>Greutate:</b> {weight_text}")
    return "\n".join(lines)


def _entry_description(entry: LastEntry) -> str:
    """Short Romanian description of the entry /sterge would remove."""
    if entry.kind == "masa":
        return f"🍽️ masă: {_esc(entry.text or '')} (<b>{entry.kcal}</b> kcal)"
    if entry.kind == "activitate":
        return f"🏃 activitate: {_esc(entry.text or '')}"
    if entry.kind == "apa":
        return f"💧 apă: <b>{entry.ml}</b> ml"
    if entry.kind == "cantar":
        return f"⚖️ greutate: <b>{_fmt_num(entry.weight_kg or 0)}</b> kg"
    return entry.kind


def format_delete_confirm(entry: LastEntry) -> str:
    return f"🗑️ <b>Ștergi ultima înregistrare?</b>\n\n{_entry_description(entry)}"


def format_delete_done(kind: str, day: DayTotals, profile: Profile | None) -> str:
    """Confirmation after a delete; for a meal, also shows the updated daily total."""
    lines = ["🗑️ <b>Înregistrare ștearsă.</b>"]
    if kind == "masa":
        lines.append("")
        lines.append(_format_day_progress(day, profile))
    return "\n".join(lines)


# --- Rezumat zilnic (P5) -------------------------------------------------------

# Shown by the 21:00 auto-summary when nothing at all was logged that day.
SUMMARY_EMPTY = "Azi n-ai înregistrat nimic. 🤔\nMâine reluăm! 💪"

# Short encouraging notes, picked by how the day went. The pick is seeded by the
# date so /sumar and the scheduled summary show the *same* note for a given day
# (PLAN.md P5 acceptance), while still varying day to day. Richer/randomised
# motivation is P9.
SUMMARY_NOTES_ON_TARGET = [
    "Zi excelentă, ai fost chiar pe țintă! 🎯",
    "Echilibru perfect azi. Ține-o tot așa! 👏",
    "Țintă atinsă — felicitări! 🌟",
]
SUMMARY_NOTES_UNDER = [
    "Mai e loc de o gustare sănătoasă. 🍎",
    "Ai rămas sub țintă — ai grijă să mănânci destul. 🥗",
    "Încă puține calorii până la țintă. 💪",
]
SUMMARY_NOTES_OVER = [
    "Ai depășit puțin ținta — mâine echilibrăm. 💪",
    "Peste țintă azi, dar nicio grijă: contează constanța. 🌱",
    "O zi mai plină — mâine o luăm lin. 🙂",
]
SUMMARY_NOTES_NO_PROFILE = [
    "Completează /profil ca să-ți pot urmări țintele. 🎯",
    "Setează-ți țintele cu /profil pentru un rezumat complet. 💡",
]


def _pick_summary_note(summary: DaySummary) -> str:
    """Choose an encouraging note based on kcal vs target (deterministic per day)."""
    rng = random.Random(summary.log_date.toordinal())
    profile = summary.profile
    if profile is None or not profile.target_kcal:
        return rng.choice(SUMMARY_NOTES_NO_PROFILE)
    ratio = summary.totals.kcal / profile.target_kcal
    if ratio < 0.9:
        return rng.choice(SUMMARY_NOTES_UNDER)
    if ratio > 1.1:
        return rng.choice(SUMMARY_NOTES_OVER)
    return rng.choice(SUMMARY_NOTES_ON_TARGET)


def _format_summary_weight(summary: DaySummary) -> str:
    """Latest known weight; if it's from an earlier day, note that date."""
    weight = summary.latest_weight
    if weight is None:
        return "—"
    text = f"{_fmt_num(weight.weight_kg)} kg"
    if not summary.weighed_today:
        text += f" <i>({weight.log_date.strftime('%d.%m')})</i>"
    return text


def format_summary(summary: DaySummary) -> str:
    """The daily summary used by both /sumar and the 21:00 auto-summary.

    Same data → same text, so the two outputs match (PLAN.md P5 acceptance).
    """
    header = f"📊 <b>Rezumat zilnic</b> ({summary.log_date.strftime('%d.%m.%Y')})"
    if summary.is_empty:
        return f"{header}\n\n{SUMMARY_EMPTY}"

    lines = [header, "", _format_day_progress(summary.totals, summary.profile), ""]

    lines.append("🍽️ <b>Mese</b>")
    if summary.meals:
        for meal in summary.meals:
            lines.append(f"• {_esc(meal.raw_text)} — <b>{meal.total_kcal}</b> kcal")
    else:
        lines.append("<i>nimic</i>")
    lines.append("")

    lines.append("🏃 <b>Activitate</b>")
    if summary.activities:
        for activity in summary.activities:
            lines.append(f"• {_esc(activity.raw_text)}")
    else:
        lines.append("<i>nimic</i>")
    lines.append("")

    lines.append(f"💧 <b>Apă:</b> {summary.water_ml} ml")
    lines.append(f"⚖️ <b>Greutate:</b> {_format_summary_weight(summary)}")
    lines.append("")
    lines.append(_pick_summary_note(summary))
    return "\n".join(lines)


# --- Raport săptămânal (P6) ----------------------------------------------------

# Shown when nothing was logged all week (no meals and no weigh-ins in the window).
SAPTAMANA_EMPTY = "Săptămâna asta n-ai înregistrat nimic. 🤔\nHai să reluăm de mâine! 💪"

# "On target" band, same as the daily note (DECISIONS.md, 2026-06-18): a day is on
# target within ±10 % of the kcal target, under below 90 %, over above 110 %.
_TARGET_UNDER = 0.9
_TARGET_OVER = 1.1


def _fmt_date_range(start: date, end: date) -> str:
    """e.g. 15.06–21.06.2026 (start without the year, end with it)."""
    return f"{start.strftime('%d.%m')}–{end.strftime('%d.%m.%Y')}"


def _zile(n: int) -> str:
    """Romanian day count: 1 → '1 zi', else 'N zile' (the window is ≤ 7 days)."""
    return f"{n} {'zi' if n == 1 else 'zile'}"


def _format_week_averages(week: WeekSummary) -> str:
    """Daily averages over the window; vs targets when a profile exists."""
    profile = week.profile
    lines = ["📊 <b>Medie zilnică</b>"]
    if profile is not None and profile.target_kcal:
        pct = round(week.avg_kcal / profile.target_kcal * 100)
        lines.append(f"🔥 Calorii: <b>{week.avg_kcal}</b>/{profile.target_kcal} kcal ({pct}%)")
        lines.append(
            f"🥩 {week.avg_protein_g}/{profile.target_protein_g} g · "
            f"🍞 {week.avg_carbs_g}/{profile.target_carbs_g} g · "
            f"🥑 {week.avg_fat_g}/{profile.target_fat_g} g"
        )
    else:
        lines.append(f"🔥 Calorii: <b>{week.avg_kcal}</b> kcal")
        lines.append(f"🥩 {week.avg_protein_g} g · 🍞 {week.avg_carbs_g} g · 🥑 {week.avg_fat_g} g")
    return "\n".join(lines)


def _format_week_targets(week: WeekSummary) -> str | None:
    """Counts of logged days that landed on / over / under the kcal target.

    Only days with a logged meal are classified (an unlogged day is *not* counted as
    "under"); needs a profile target. Returns ``None`` when neither applies.
    """
    profile = week.profile
    if profile is None or not profile.target_kcal:
        return None
    logged = [day for day in week.days if day.has_meals]
    if not logged:
        return None
    on = over = under = 0
    for day in logged:
        ratio = day.kcal / profile.target_kcal
        if ratio < _TARGET_UNDER:
            under += 1
        elif ratio > _TARGET_OVER:
            over += 1
        else:
            on += 1
    return (
        "🎯 <b>Zile vs țintă</b>\n"
        f"✅ Pe țintă: {_zile(on)} · 📈 Peste: {_zile(over)} · 📉 Sub: {_zile(under)}"
    )


def _format_week_extremes(week: WeekSummary) -> str | None:
    """Best (closest to target) and worst (furthest) logged day, by % deviation."""
    profile = week.profile
    if profile is None or not profile.target_kcal:
        return None
    logged = [day for day in week.days if day.has_meals]
    if not logged:
        return None
    target = profile.target_kcal

    def deviation(day: DayStat) -> float:
        return abs(day.kcal / target - 1)

    best = min(logged, key=deviation)
    lines = [
        f"⭐ <b>Cea mai bună zi:</b> {best.log_date.strftime('%d.%m')} — "
        f"{best.kcal} kcal ({round(best.kcal / target * 100)}% din țintă)"
    ]
    worst = max(logged, key=deviation)
    if worst.log_date != best.log_date:
        lines.append(
            f"📌 <b>Cea mai îndepărtată de țintă:</b> {worst.log_date.strftime('%d.%m')} — "
            f"{worst.kcal} kcal ({round(worst.kcal / target * 100)}% din țintă)"
        )
    return "\n".join(lines)


def _format_week_weight(week: WeekSummary) -> str:
    """Weight trend: first → last weigh-in within the window, with the change."""
    weigh_ins = week.weigh_ins
    if len(weigh_ins) >= 2:
        first, last = weigh_ins[0], weigh_ins[-1]
        delta = last.weight_kg - first.weight_kg
        if delta > 0.05:
            change = f"📈 +{_fmt_num(delta)} kg"
        elif delta < -0.05:
            change = f"📉 {_fmt_num(delta)} kg"
        else:
            change = "➡️ stabilă"
        return (
            f"⚖️ <b>Greutate:</b> {_fmt_num(first.weight_kg)} → "
            f"{_fmt_num(last.weight_kg)} kg ({change})"
        )
    if len(weigh_ins) == 1:
        return f"⚖️ <b>Greutate:</b> {_fmt_num(weigh_ins[0].weight_kg)} kg (o singură cântărire)"
    if week.latest_weight is not None:
        weight = week.latest_weight
        return (
            f"⚖️ <b>Greutate:</b> {_fmt_num(weight.weight_kg)} kg "
            f"<i>({weight.log_date.strftime('%d.%m')})</i> — fără cântăriri săptămâna asta"
        )
    return "⚖️ <b>Greutate:</b> —"


def format_weekly_report(week: WeekSummary) -> str:
    """The weekly report used by both /saptamana and the Sunday-night auto-report.

    Same data → same text, so the two outputs match (PLAN.md P6 acceptance).
    """
    header = f"📈 <b>Raport săptămânal</b> ({_fmt_date_range(week.start_date, week.end_date)})"
    if week.is_empty:
        return f"{header}\n\n{SAPTAMANA_EMPTY}"

    blocks = [header, "", f"🍽️ <b>Mese:</b> {week.days_with_meals}/{week.num_days} zile", ""]
    blocks.append(_format_week_averages(week))

    for section in (_format_week_targets(week), _format_week_extremes(week)):
        if section is not None:
            blocks.append("")
            blocks.append(section)

    blocks.append("")
    blocks.append(_format_week_weight(week))

    if week.profile is None or not week.profile.target_kcal:
        blocks.append("")
        blocks.append("💡 Scrie /profil ca să-ți pot raporta și zilele pe țintă.")
    return "\n".join(blocks)
