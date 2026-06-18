"""Profile onboarding (`/profil`, an FSM) and target viewing/adjustment (`/tinte`)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .. import repository, strings
from ..targets import (
    Activity,
    Goal,
    Sex,
    Targets,
    compute_targets,
    macros_for,
)

router = Router(name="profile")

# Input bounds, kept next to the matching error strings.
AGE_MIN, AGE_MAX = 10, 100
HEIGHT_MIN, HEIGHT_MAX = 100.0, 250.0
WEIGHT_MIN, WEIGHT_MAX = 30.0, 300.0
KCAL_MIN, KCAL_MAX = 800, 6000


class ProfileForm(StatesGroup):
    sex = State()
    age = State()
    height = State()
    weight = State()
    activity = State()
    goal = State()


def _reverse[T](mapping: dict[T, str]) -> dict[str, T]:
    """Map a button caption back to its enum value."""
    return {label: key for key, label in mapping.items()}


_SEX_BY_LABEL = _reverse(strings.SEX_BUTTONS)
_ACTIVITY_BY_LABEL = _reverse(strings.ACTIVITY_BUTTONS)
_GOAL_BY_LABEL = _reverse(strings.GOAL_BUTTONS)


def _choice_keyboard(captions: list[str]) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for caption in captions:
        builder.button(text=caption)
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def _parse_number(text: str) -> float | None:
    """Parse a number, accepting a Romanian decimal comma. ``None`` if invalid."""
    try:
        return float(text.strip().replace(",", "."))
    except ValueError:
        return None


# --- /profil (FSM) ------------------------------------------------------------


@router.message(Command("profil"))
async def start_profile(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(ProfileForm.sex)
    await message.answer(
        strings.PROFIL_START,
        reply_markup=_choice_keyboard(list(strings.SEX_BUTTONS.values())),
    )


@router.message(Command("renunta"))
async def cancel_profile(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        return
    await state.clear()
    await message.answer(strings.PROFIL_CANCELLED, reply_markup=ReplyKeyboardRemove())


@router.message(ProfileForm.sex, F.text)
async def set_sex(message: Message, state: FSMContext) -> None:
    sex = _SEX_BY_LABEL.get(message.text or "")
    if sex is None:
        await message.answer(
            strings.PROFIL_PICK_BUTTON,
            reply_markup=_choice_keyboard(list(strings.SEX_BUTTONS.values())),
        )
        return
    await state.update_data(sex=sex.value)
    await state.set_state(ProfileForm.age)
    await message.answer(strings.PROFIL_ASK_AGE, reply_markup=ReplyKeyboardRemove())


@router.message(ProfileForm.age, F.text)
async def set_age(message: Message, state: FSMContext) -> None:
    value = _parse_number(message.text or "")
    if value is None or value != int(value) or not (AGE_MIN <= value <= AGE_MAX):
        await message.answer(strings.ERR_AGE)
        return
    await state.update_data(age=int(value))
    await state.set_state(ProfileForm.height)
    await message.answer(strings.PROFIL_ASK_HEIGHT)


@router.message(ProfileForm.height, F.text)
async def set_height(message: Message, state: FSMContext) -> None:
    value = _parse_number(message.text or "")
    if value is None or not (HEIGHT_MIN <= value <= HEIGHT_MAX):
        await message.answer(strings.ERR_HEIGHT)
        return
    await state.update_data(height_cm=value)
    await state.set_state(ProfileForm.weight)
    await message.answer(strings.PROFIL_ASK_WEIGHT)


@router.message(ProfileForm.weight, F.text)
async def set_weight(message: Message, state: FSMContext) -> None:
    value = _parse_number(message.text or "")
    if value is None or not (WEIGHT_MIN <= value <= WEIGHT_MAX):
        await message.answer(strings.ERR_WEIGHT)
        return
    await state.update_data(weight_kg=value)
    await state.set_state(ProfileForm.activity)
    await message.answer(
        strings.PROFIL_ASK_ACTIVITY,
        reply_markup=_choice_keyboard(list(strings.ACTIVITY_BUTTONS.values())),
    )


@router.message(ProfileForm.activity, F.text)
async def set_activity(message: Message, state: FSMContext) -> None:
    activity = _ACTIVITY_BY_LABEL.get(message.text or "")
    if activity is None:
        await message.answer(
            strings.PROFIL_PICK_BUTTON,
            reply_markup=_choice_keyboard(list(strings.ACTIVITY_BUTTONS.values())),
        )
        return
    await state.update_data(activity=activity.value)
    await state.set_state(ProfileForm.goal)
    await message.answer(
        strings.PROFIL_ASK_GOAL,
        reply_markup=_choice_keyboard(list(strings.GOAL_BUTTONS.values())),
    )


@router.message(ProfileForm.goal, F.text)
async def set_goal(
    message: Message,
    state: FSMContext,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    goal = _GOAL_BY_LABEL.get(message.text or "")
    if goal is None:
        await message.answer(
            strings.PROFIL_PICK_BUTTON,
            reply_markup=_choice_keyboard(list(strings.GOAL_BUTTONS.values())),
        )
        return

    data = await state.update_data(goal=goal.value)
    await state.clear()

    targets = compute_targets(
        sex=Sex(data["sex"]),
        weight_kg=data["weight_kg"],
        height_cm=data["height_cm"],
        age=data["age"],
        activity=Activity(data["activity"]),
        goal=Goal(data["goal"]),
    )
    async with sessionmaker() as session:
        profile = await repository.upsert_profile(
            session,
            telegram_user_id=message.from_user.id,
            sex=data["sex"],
            age=data["age"],
            height_cm=data["height_cm"],
            weight_kg=data["weight_kg"],
            activity=data["activity"],
            goal=data["goal"],
            targets=targets,
        )
        text = strings.format_profile_saved(profile)

    await message.answer(text, reply_markup=ReplyKeyboardRemove())


# --- /tinte (view & adjust) ---------------------------------------------------


@router.message(Command("tinte"))
async def show_or_set_targets(
    message: Message,
    command: CommandObject,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with sessionmaker() as session:
        profile = await repository.get_profile(session, message.from_user.id)
        if profile is None:
            await message.answer(strings.TINTE_NO_PROFILE)
            return

        arg = (command.args or "").strip()
        if not arg:
            computed = compute_targets(
                sex=Sex(profile.sex),
                weight_kg=profile.weight_kg,
                height_cm=profile.height_cm,
                age=profile.age,
                activity=Activity(profile.activity),
                goal=Goal(profile.goal),
            ).kcal
            await message.answer(strings.format_targets_view(profile, computed))
            return

        value = _parse_number(arg)
        if value is None or value != int(value) or not (KCAL_MIN <= value <= KCAL_MAX):
            await message.answer(strings.ERR_TINTE_KCAL)
            return

        kcal = int(value)
        macros = macros_for(kcal, profile.weight_kg)
        new_targets = Targets(
            kcal=kcal,
            protein_g=macros.protein_g,
            carbs_g=macros.carbs_g,
            fat_g=macros.fat_g,
        )
        profile = await repository.update_targets(
            session, profile, manual_kcal=kcal, targets=new_targets
        )
        await message.answer(strings.format_targets_updated(profile))
