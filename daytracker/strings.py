"""All user-facing strings, in Romanian.

Kept in one place so the bot's voice stays consistent and easy to edit.
Messages use Telegram HTML formatting (the bot's default parse mode).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .targets import Activity, Goal, Sex

if TYPE_CHECKING:
    from .models import Profile

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
