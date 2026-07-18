from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="💰 Hamyon")
        ],
        [
            KeyboardButton(text="🤝 P2P Market"),
            KeyboardButton(text="🎰 Baraban")
        ],
        [
            KeyboardButton(text="👤 Profil"),
            KeyboardButton(text="⚙️ Sozlamalar")
        ]
    ],
    resize_keyboard=True
)
