import os
import logging
import re
import paramiko
from dotenv import load_dotenv
import psycopg2
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext


load_dotenv()


TOKEN = os.getenv("TOKEN")
HOST = os.getenv("RM_HOST")
HOSTDB = os.getenv("DB_HOST")
PORT = int(os.getenv("RM_PORT"))
NAME = os.getenv("RM_USER")
PASSWORD = os.getenv("RM_PASSWORD")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = int(os.getenv("DB_PORT"))
DB = os.getenv("DB_DATABASE")

logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет, {user.full_name}!')

def help_command(update: Update, context):
    update.message.reply_text('Help!')

def store_data_auto(update: Update, context: CallbackContext, data_type, data_list):
    try:
        connection = psycopg2.connect(user=DB_USER, password=DB_PASSWORD, host=HOSTDB, port=DB_PORT, database=DB)
        cursor = connection.cursor()
        for data in data_list:
            cursor.execute(f"INSERT INTO {data_type} ({data_type[:-1]}) VALUES (%s) ON CONFLICT DO NOTHING", (data,))
        connection.commit()
    except psycopg2.Error as e:
        update.message.reply_text(f"Ошибка при записи в базу данных: {e}")
        logger.error(f"Ошибка при записи в базу данных: {e}")
    finally:
        if connection is not None:
            cursor.close()
            connection.close()


def confirm_phone_numbers(update: Update, context: CallbackContext):
    user_input = update.message.text.strip().lower()
    if user_input == 'да':
        store_data_auto(update, context, 'phone_numbers', context.user_data.get('phone_numbers', []))
        get_phone_numbers(update, context)
    elif user_input == 'нет':
        update.message.reply_text('Номера телефона не будут сохранены в базе данных.')
    else:
        update.message.reply_text('Пожалуйста, введите "Да" или "Нет".')

    return ConversationHandler.END

def find_phone_number_command(update: Update, context: CallbackContext):
    update.message.reply_text('Введите текст для поиска номера телефона:')
    return 'find_phone_number'

def find_phone_number(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    phone_numbers = find_numbers(text)

    if phone_numbers:
        context.user_data['phone_numbers'] = phone_numbers
        update.message.reply_text(f'Найденные номера телефонов: {", ".join(phone_numbers)}')


        update.message.reply_text('Хотите сохранить эти номера в базе данных? (Да/Нет)')
        return 'confirm_phone_numbers'
    else:
        update.message.reply_text('Номера телефона не найдены')

    return ConversationHandler.END

def find_email_command(update: Update, context: CallbackContext):
    update.message.reply_text('Введите текст для поиска адреса электронной почты:')
    return 'find_email'

def find_email(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    emails = find_emails(text)

    if emails:
        context.user_data['email_addresses'] = emails
        update.message.reply_text(f'Найденные адреса электронной почты: {", ".join(emails)}')


        update.message.reply_text('Хотите сохранить эти адреса электронной почты в базе данных? (Да/Нет)')
        return 'confirm_email_addresses'
    else:
        update.message.reply_text('Адреса электронной почты не найдены')

    return ConversationHandler.END


def confirm_email_addresses(update: Update, context: CallbackContext):
    user_input = update.message.text.strip().lower()
    if user_input == 'да':

        store_data_auto(update, context, 'emails', context.user_data.get('email_addresses', []))
        get_emails(update, context)
    elif user_input == 'нет':
        update.message.reply_text('Email не будут сохранены в базе данных.')
    else:
        update.message.reply_text('Пожалуйста, введите "Да" или "Нет".')

    return ConversationHandler.END




def find_numbers(text):
    phone_regex = re.compile(r'(\+?\d{1}\s*[-\.\(]?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{2}[-\.\s]?\d{2}|\d{1}\s*[-\.\(]?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{2}[-\.\s]?\d{2}|\+?\d{1}\s*[-\.\(]?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{2}[-\.\s]?\d{2}|\d{1}\s*[-\.\(]?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{2}[-\.\s]?\d{2}|\d{1}\s*[-\.\(]?\d{3}\)?[-\.\s]?\d{3}[-\.\s]?\d{2}[-\.\s]?\d{2})')
    return phone_regex.findall(text)

def find_emails(text):
    email_regex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
    return email_regex.findall(text)

def get_emails(update: Update, context: CallbackContext):
    try:
        connection = psycopg2.connect(user=DB_USER, password=DB_PASSWORD, host=HOSTDB, port=DB_PORT, database=DB)
        cursor = connection.cursor()
        cursor.execute("SELECT email FROM emails;")
        emails = cursor.fetchall()
        if emails:
            email_list = [email[0] for email in emails]
            email_text = "\n".join(email_list)
            update.message.reply_text(f'Вот обновленные известные адреса электронной почты:\n{email_text}')
        else:
            update.message.reply_text('Адреса электронной почты не найдены')
    except psycopg2.Error as e:
        update.message.reply_text(f'Ошибка при работе с PostgreSQL: {e}')
    finally:
        if connection is not None:
            cursor.close()
            connection.close()

def get_phone_numbers(update: Update, context: CallbackContext):
    try:
        connection = psycopg2.connect(user=DB_USER, password=DB_PASSWORD, host=HOSTDB, port=DB_PORT, database=DB)
        cursor = connection.cursor()
        cursor.execute("SELECT phone_number FROM phone_numbers;")
        phone_numbers = cursor.fetchall()
        if phone_numbers:
            phone_list = [phone[0] for phone in phone_numbers]
            phone_text = "\n".join(phone_list)
            update.message.reply_text(f'Вот номера телефонов:\n{phone_text}')
        else:
            update.message.reply_text('Номера телефона не найдены')
    except psycopg2.Error as e:
        update.message.reply_text(f'Ошибка при работе с PostgreSQL: {e}')
    finally:
        if connection is not None:
            cursor.close()
            connection.close()

def verify_password_command(update: Update, context):
    update.message.reply_text('Введите пароль для проверки его сложности:')
    return 'verify_password'


def verify_password(update: Update, context):
    user_input = update.message.text.strip()

    if is_strong_password(user_input):
        update.message.reply_text('Пароль сложный')
    else:
        update.message.reply_text('Пароль простой')

    return ConversationHandler.END


def is_strong_password(password):
    password_regex = re.compile(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$')
    return bool(password_regex.match(password))


def execute_ssh_command(host, port, username, password, command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(hostname=host, port=port, username=username, password=password)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        client.close()
        if error:
            return f"Error: {error}"
        else:
            return output
    except Exception as e:
        return f"An error occurred: {str(e)}"


def get_release(update: Update, context):
    command = "cat /etc/*release"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def get_uname(update: Update, context):
    command = "uname -a"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def get_uptime(update: Update, context):
    command = "uptime"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def get_df(update: Update, context):
    command = "df -h"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def get_free(update: Update, context):
    command = "free -h"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def get_mpstat(update: Update, context):
    command = "mpstat"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def get_w(update: Update, context):
    command = "w"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def get_auths(update: Update, context):
    command = "last -n 10"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def get_critical(update: Update, context):
    command = "tail -n 5 /var/log/syslog"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def get_ps(update: Update, context):
    command = "ps"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def get_ss(update: Update, context):
    command = "ss -tulwn"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def get_apt_list(update: Update):
    text = update.message.text.strip()
    if len(text.split()) > 1:
        package_name = " ".join(text.split()[1:])
        command = f"apt-cache show {package_name} 2>/dev/null"
        result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
        if result:
            update.message.reply_text(result)
        else:
            update.message.reply_text(f"Пакет '{package_name}' не найден.")
    else:
        command = "apt list --installed 2>/dev/null"
        result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
        for line in result.split('\n'):
            update.message.reply_text(line)
        update.message.reply_text(
            "Если вас интересует информация о каком-то пакете, введите '/get_apt_list название_пакета'. Например, '/get_apt_list python3'.")


def get_services(update: Update, context):
    command = "service --status-all"
    result = execute_ssh_command(HOST, PORT, NAME, PASSWORD, command)
    update.message.reply_text(result)


def list_commands(update: Update, context):
    command_list = [
        "/start - Начать взаимодействие с ботом",
        "/help - Получить справку",
        "/get_release - Получить информацию о релизе системы",
        "/get_uname - Получить информацию о версии ядра",
        "/get_uptime - Получить информацию о времени работы системы",
        "/get_df - Получить информацию о дисковом пространстве",
        "/get_free - Получить информацию о доступной памяти",
        "/get_mpstat - Получить статистику процессора",
        "/get_w - Получить список пользователей, подключенных к системе",
        "/get_auths - Получить список последних авторизаций",
        "/get_critical - Получить критические записи из журнала системы",
        "/get_ps - Получить список текущих процессов",
        "/get_ss - Получить список открытых сокетов",
        "/get_apt_list - Получить список установленных пакетов",
        "/get_services - Получить список всех служб",
        "/verify_password - Проверить сложность пароля",
        "/find_phone_number - Найти номера телефонов в тексте",
        "/find_email - Найти адреса электронной почты в тексте",
        "/list_commands - Показать список всех доступных команд",
        "/get_repl_logs - Получить логи репликации PostgreSQL"
    ]
    update.message.reply_text("\n".join(command_list))

def get_repl_logs(update: Update, context: CallbackContext):
    log_directory_path = "/bitnami/postgresql/data/log/"

    if os.path.exists(log_directory_path):
        log_files = [f for f in os.listdir(log_directory_path) if f.endswith('.csv')]

        relevant_logs = []

        for log_file_name in log_files:
            log_file_path = os.path.join(log_directory_path, log_file_name)

            with open(log_file_path, "r") as log_file:
                logs = log_file.readlines()

                for log in logs:
                    if "starting PostgreSQL" in log:
                        relevant_logs.append(log)
                    elif "aborting any active transactions" in log:
                        relevant_logs.append(log)
                    elif "database system is ready to accept connections" in log:
                        relevant_logs.append(log)

        if relevant_logs:
            for log in relevant_logs:
                context.bot.send_message(chat_id=update.effective_chat.id, text=log)
        else:
            update.message.reply_text("Не найдены соответствующие логи.")
    else:
        update.message.reply_text("Файлы с логами не найдены.")

def echo(update: Update, context):
    update.message.reply_text(update.message.text)


def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler_verify_password = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_password_command)],
        states={'verify_password': [MessageHandler(Filters.text & ~Filters.command, verify_password)]},
        fallbacks=[]
    )
    conv_handler_find_phone_number = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', find_phone_number_command)],
        states={'find_phone_number': [MessageHandler(Filters.text & ~Filters.command, find_phone_number)],
                'confirm_phone_numbers': [MessageHandler(Filters.text & ~Filters.command, confirm_phone_numbers)]},
        fallbacks=[]
    )

    conv_handler_find_email = ConversationHandler(
        entry_points=[CommandHandler('find_email', find_email_command)],
        states={'find_email': [MessageHandler(Filters.text & ~Filters.command, find_email)],
                'confirm_email_addresses': [MessageHandler(Filters.text & ~Filters.command, confirm_email_addresses)]},
        fallbacks=[]
    )
    dp.add_handler(conv_handler_find_phone_number)
    dp.add_handler(conv_handler_find_email)
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_apt_list", get_apt_list))
    dp.add_handler(CommandHandler("get_services", get_services))
    dp.add_handler(conv_handler_verify_password)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    dp.add_handler(CommandHandler("list_commands", list_commands))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
