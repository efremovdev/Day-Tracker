"""Common commands available from the start: /start and /ajutor."""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from .. import strings

router = Router(name="common")


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(strings.START)


@router.message(Command("ajutor"))
async def handle_help(message: Message) -> None:
    await message.answer(strings.HELP)
