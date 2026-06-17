"""All user-facing strings, in Romanian.

Kept in one place so the bot's voice stays consistent and easy to edit.
Messages use Telegram HTML formatting (the bot's default parse mode).
"""

from __future__ import annotations

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
