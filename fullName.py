# 1. Загрузка библиотек
import logging
import pandas as pd
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import Router
import asyncio
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# 2. Подготовка файлов
df_path = 'russia2english.xlsx'
df = pd.read_excel(df_path)

ministerial_decree_path= 'ministerial_decree.txt'
with open(ministerial_decree_path, 'r', encoding='utf-8') as file:
    ministerial_decree_text = file.read()

positive_messages_module = 'positive_messages'
positive_messages = __import__(positive_messages_module).positive_messages

# 3. Определение состояний
class Form(StatesGroup):
    waiting_for_fio = State()

# 4. Инициализация объектов, подключение router, настройка логирования
TOKEN = os.getenv('TOKEN')
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)
logging.basicConfig(level=logging.INFO)

# 5. Установка команд
async def set_commands(bot: Bot):
    commands = [
        types.BotCommand(command="/prikaz", description="выведет Приказ МИД России от 12.02.2020 N 2113"),
        types.BotCommand(command="/tablica", description="выведет Таблицу транслитерации кириллических знаков"),
        types.BotCommand(command="/fio", description="попросит ввести Вас свои ФИО для транслитерации"),
        types.BotCommand(command="/positive", description="скажет что-то позитивное Вам")
    ]
    await bot.set_my_commands(commands)

# 6. Обработка команды /start
@router.message(Command("start"))
async def proccess_command_start(message: Message):
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    logging.info(f'{user_name} {user_id} запустил бота')

    # Создание клавиатуры с интерактивными кнопками
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Приказ", callback_data="prikaz")],
            [InlineKeyboardButton(text="Таблица", callback_data="tablica")],
            [InlineKeyboardButton(text="ФИО", callback_data="fio")],
            [InlineKeyboardButton(text="Позитив", callback_data="positive")],
        ]
    )

    text = f"Привет, {user_name}. Моя основная задача делать транслитерацию кириллических знаков, в основном это требуется для правильного перевода ФИО на английский язык. Это требует приказ МИД России. Но я также могу предоставить Вам определённую информацию на эту тему. Вы можете управлять мной, отправляя следующие команды:"
    
    await message.answer(text, reply_markup=keyboard)

# 7. Обработка нажатий на инлайн-кнопки
@router.callback_query()
async def handle_callback_query(callback_query: types.CallbackQuery, state: FSMContext):
    command = callback_query.data  # Получаем данные из callback_data кнопки
    if command == "prikaz":
        await send_prikaz(callback_query.message)
    elif command == "tablica":
        await send_table(callback_query.message)
    elif command == "fio":
        await proccess_command_fio(callback_query.message, state)  # передаем state
    elif command == "positive":
        await send_positive_message(callback_query.message)

    # Отправляем уведомление о нажатии (чтобы закрыть всплывающее уведомление в Telegram)
    await callback_query.answer()

# 8. Обработка команды /prikaz
@router.message(Command("prikaz"))
async def send_prikaz(message: Message):
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    logging.info(f'{user_name} {user_id} запустил команду /prikaz')
    await message.answer(ministerial_decree_text)

# 9. Обработка команды /tablica
@router.message(Command("tablica"))
async def send_table(message: types.Message):
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    logging.info(f'{user_name} {user_id} запустил команду /tablica')

    # Преобразуем DataFrame в строковый формат с заголовками, но без индексов
    table_string = df.to_string(index=False)

    # Отправляем текстовую таблицу
    await message.answer(table_string)

# 10. Обработка команды /fio с использованием FSM
@router.message(Command("fio"))
async def proccess_command_fio(message: Message, state: FSMContext):
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    logging.info(f'Имя: {user_name}, ID: {user_id}')
    text = f"Введите пожалуйста свои ФИО"
    await message.answer(text)
    
    # Устанавливаем состояние ожидания ФИО
    await state.set_state(Form.waiting_for_fio)

# 11. Обработка следующего сообщения после /fio
@router.message(Form.waiting_for_fio)
async def process_fio_input(message: types.Message, state: FSMContext):
    user_name = message.from_user.full_name
    user_id = message.from_user.id
    user_fio = message.text
    logging.info(f'Получено ФИО от {user_name} {user_id}: {user_fio}')
    
    # Здесь можно выполнить транслитерацию ФИО
    result = transliterate_fio(user_fio)
    await message.answer(f"Ваши ФИО в транслитерации: {result}")
    
    # Завершаем состояние ожидания ФИО
    await state.clear()

# 12. Транслитерация
def transliterate_fio(fio):
    result = []
    for letter in fio:
        if letter == " ":
            result.append(" ")
        elif letter.upper() in df['RUS'].values:
            corresponding_value = df.loc[df['RUS'] == letter.upper(), 'ENG'].values[0]
            result.append(corresponding_value)
        else:
            result.append(None)
    return ''.join([str(r) if r is not None else "" for r in result]).strip()

# 13. Обработка команды /positive
@router.message(Command("positive"))
async def send_positive_message(message: Message):
    import random
    positive_message = random.choice(positive_messages)
    await message.answer(positive_message)

# 14. Запуск бота
if __name__ == '__main__':
    async def main():
        await dp.start_polling(bot, skip_updates=True)

    asyncio.run(main())
