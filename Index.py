import logging
import telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import sqlite3
import datetime

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Определение состояний для функций
NEW_RECORD, SERVICE_NAME, CURRENT_MILEAGE, SERVICE_DATE, SERVICE_COST, RECEIPT_PHOTO = range(6)

# Создание и подключение к базе данных
def create_connection():
    conn = sqlite3.connect("C:/Users/MRROOT/Downloads/2fa/AutoBot/car_owner_bot.db")
    return conn

# Инициализация таблицы для записей
def initialize_records_table():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS records
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, service_name TEXT, current_mileage INTEGER, service_date TEXT, service_cost REAL, receipt_photo TEXT)''')
    conn.commit()
    conn.close()

# Функция старта
def start(update: Update, context):
    user = update.effective_user
    logger.info(f"User {user.username} started the conversation.")
    keyboard = [
        [
            "Добавить новую запись",
            "Добавить ТО"
        ],
        [
            "Посмотреть записи",
            "Следующее ТО"
        ]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("Привет! Я бот для автовладельцев. Выберите, что вы хотите сделать:", reply_markup=reply_markup)


# Ваш код для функций добавления новой записи, просмотра записей, добавления ТО, следующего ТО

def process_message(update: Update, context: CallbackContext):
    message = update.message.text

    if message == 'Добавить новую запись':
        update.message.reply_text("Введите название работы:")
        return SERVICE_NAME
    elif message == 'Добавить ТО':
            # Обработка для добавления ТО
        pass
    elif message == 'Посмотреть записи':
        return view_records(update, context)
    elif message == 'Следующее ТО':
        # Код для обработки кнопки "Следующее ТО"
        pass
    else:
        update.message.reply_text("Произошла ошибка при обработке вашего запроса. Попробуйте еще раз.")

# Обработка для добавления новой записи
def get_mileage(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_data["work_name"] = update.message.text
    update.message.reply_text("Введите текущий пробег автомобиля:")
    return CURRENT_MILEAGE

def get_date(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_data["mileage"] = update.message.text
    update.message.reply_text("Введите дату выполнения работы:")
    return SERVICE_DATE

def get_cost(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_data["date"] = update.message.text
    update.message.reply_text("Введите стоимость работы (если есть):")
    return SERVICE_COST

def get_photo(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_data["cost"] = update.message.text
    update.message.reply_text("Прикрепите фотографию чека/акта выполненных работы/фото машины или отправьте 'Пропустить', если не хотите добавлять фото:")
    return RECEIPT_PHOTO

# Обработка для вывода записей

def view_records(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, service_name, service_date FROM records WHERE user_id = ?", (user_id,))
    records = cursor.fetchall()
    conn.close()

    if not records:
        update.message.reply_text("У вас пока нет записей.")
        return

    keyboard = []

    for record in records:
        record_id, service_name, service_date = record
        button_text = f"{service_name} ({service_date})"
        button = InlineKeyboardButton(text=button_text, callback_data=f"record_{record_id}")
        keyboard.append([button])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Выберите запись для просмотра:", reply_markup=reply_markup)

def record_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    record_id = query.data.split("_")[1]
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT service_name, current_mileage, service_date, service_cost, receipt_photo FROM records WHERE id = ?", (record_id,))
    record = cursor.fetchone()
    conn.close()

    if not record:
        query.edit_message_text("Запись не найдена.")
        return

    service_name, current_mileage, service_date, service_cost, receipt_photo = record
    record_text = f"\u2514 <b>Название:</b> {service_name}\n\u2514 <b>Пробег:</b> {current_mileage}\n\u2514 <b>Дата:</b> {service_date}\n\u2514 <b>Стоимость:</b> {service_cost}"
    query.edit_message_text(text=record_text, parse_mode=telegram.ParseMode.HTML)
    if receipt_photo:
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=receipt_photo)


def save_record(update: Update, context: CallbackContext):
    user_data = context.user_data
    if update.message.photo:
        user_data["photo"] = update.message.photo[-1].file_id
    else:
        user_data["photo"] = None

    # Сохраняем запись в базу данных
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO records (user_id, service_name, current_mileage, service_date, service_cost, receipt_photo) VALUES (?, ?, ?, ?, ?, ?)", (update.effective_user.id, user_data["work_name"], user_data["mileage"], user_data["date"], user_data["cost"], user_data["photo"]))
    conn.commit()
    conn.close()

    update.message.reply_text("Запись успешно добавлена!")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Добавление записи отменено.")
    return ConversationHandler.END

def main():
    # Создаем Updater и передаем токен вашего бота
    updater = Updater("Token", use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(record_callback))

    # Запрос для Добавить запись
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text, process_message)],
        states={
            SERVICE_NAME: [MessageHandler(Filters.text, get_mileage)],
            CURRENT_MILEAGE: [MessageHandler(Filters.text, get_date)],
            SERVICE_DATE: [MessageHandler(Filters.text, get_cost)],
            SERVICE_COST: [MessageHandler(Filters.text, get_photo), MessageHandler(Filters.photo, save_record)],
            RECEIPT_PHOTO: [MessageHandler(Filters.text, save_record), MessageHandler(Filters.photo, save_record)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )


    dp.add_handler(conv_handler)

    # Запускаем бота
    updater.start_polling()

    # Блокируем до тех пор, пока бот не будет остановлен (например, с помощью Ctrl + C)
    updater.idle()





if __name__ == '__main__':
    main()
