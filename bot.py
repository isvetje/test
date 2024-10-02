import telebot
import time
import datetime
import threading
import pytz
import logging
import json
import os
from collections import deque
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_TOKEN = '6840924601:AAGjdKnKN27L9gWRNEWMRWKoc-Syzrasvlw'
ADMIN_ID = 1703970055
bot = telebot.TeleBot(API_TOKEN)

def load_channels():
    if os.path.exists('channels.json'):
        with open('channels.json', 'r') as f:
            return json.load(f)
    return {'public_channels': [], 'private_channel_ids': []}

def save_channels(channels):
    with open('channels.json', 'w') as f:
        json.dump(channels, f)

channels = load_channels()

messages_queue = deque()
sent_messages = set()
user_state = 'main_menu'

TIMEZONE = pytz.timezone('Africa/Algiers')

posting_settings = {
    'start_time': None,
    'end_time': None,
    'interval': None
}

def load_settings():
    if os.path.exists('settings.json'):
        with open('settings.json', 'r') as f:
            return json.load(f)
    return {'start_time': None, 'end_time': None, 'interval': None}

def save_settings():
    with open('settings.json', 'w') as f:
        json.dump(posting_settings, f)

def get_current_time():
    return datetime.datetime.now(TIMEZONE).time()

def is_posting_time():
    if None in posting_settings.values():
        return False
    
    now = get_current_time()
    start = datetime.datetime.strptime(posting_settings['start_time'], "%H:%M").time()
    end = datetime.datetime.strptime(posting_settings['end_time'], "%H:%M").time()
    
    if start <= end:
        return start <= now <= end
    else:
        return now >= start or now <= end

def publish_message():
    global sent_messages
    while True:
        if is_posting_time() and messages_queue:
            for _ in range(len(messages_queue)):
                message = messages_queue.popleft()
                message_id = hash(str(message))

                if message_id not in sent_messages:
                    for channel in channels['public_channels']:
                        try:
                            if message['type'] == 'photo':
                                bot.send_photo(channel, photo=message['file_id'], caption=message['caption_text'])
                            elif message['type'] == 'video':
                                bot.send_video(channel, video=message['file_id'], caption=message['caption_text'])
                            else:
                                bot.send_message(channel, message['caption_text'])
                            logger.info(f"تم إرسال الرسالة بنجاح إلى {channel}")
                        except Exception as e:
                            logger.error(f"حدث خطأ أثناء إرسال الرسالة إلى {channel}: {str(e)}")

                    for channel_id in channels['private_channel_ids']:
                        try:
                            if message['type'] == 'photo':
                                bot.send_photo(channel_id, photo=message['file_id'], caption=message['caption_text'])
                            elif message['type'] == 'video':
                                bot.send_video(channel_id, message['file_id'], caption=message['caption_text'])
                            else:
                                bot.send_message(channel_id, message['caption_text'])
                            logger.info(f"تم إرسال الرسالة بنجاح إلى القناة الخاصة {channel_id}")
                        except Exception as e:
                            logger.error(f"حدث خطأ أثناء إرسال الرسالة إلى القناة الخاصة {channel_id}: {str(e)}")

                    sent_messages.add(message_id)
                    break
                else:
                    messages_queue.append(message)

            time.sleep(int(posting_settings['interval']) * 60)
        else:
            time.sleep(60)

def is_admin(message):
    return message.from_user.id == ADMIN_ID

def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton('🔧 تغيير الإعدادات'),
        KeyboardButton('📊 عرض الإعدادات'),
        KeyboardButton('➕ إضافة محتوى'),
        KeyboardButton('📋 عرض المحتوى'),
        KeyboardButton('🗑 حذف القائمة'),
        KeyboardButton('➕ إضافة قناة عامة'),
        KeyboardButton('➕ إضافة قناة خاصة'),
        KeyboardButton('🗑 إزالة قناة عامة'),
        KeyboardButton('🗑 إزالة قناة خاصة'),
    ]
    keyboard.add(*buttons)
    return keyboard

@bot.message_handler(commands=['start'])
def handle_start(message):
    if not is_admin(message):
        bot.reply_to(message, "😐.")
        return

    global user_state
    user_state = 'main_menu'
    bot.send_message(message.chat.id, "🌟 مرحبًا بك في لوحة التحكم الخاصة بالبوت! 🌟\n\nماذا تريد أن تفعل الآن؟", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: message.text == '🔧 تغيير الإعدادات' and is_admin(message))
def change_settings(message):
    global user_state
    user_state = 'setting_start_time'
    bot.reply_to(message, "🕒 الرجاء إدخال وقت البدء بالتنسيق HH:MM")

@bot.message_handler(func=lambda message: user_state == 'setting_start_time' and is_admin(message))
def process_start_time(message):
    try:
        time.strptime(message.text, "%H:%M")
        posting_settings['start_time'] = message.text
        
        global user_state
        user_state = 'setting_end_time'
        bot.reply_to(message, f"✅ تم تعيين وقت البدء إلى {message.text}.\n\n🕒 الآن، أدخل وقت الانتهاء بالتنسيق HH:MM")
    except ValueError:
        bot.reply_to(message, "❌ تنسيق غير صحيح. الرجاء استخدام HH:MM")

@bot.message_handler(func=lambda message: user_state == 'setting_end_time' and is_admin(message))
def process_end_time(message):
    try:
        time.strptime(message.text, "%H:%M")
        posting_settings['end_time'] = message.text
        
        global user_state
        user_state = 'setting_interval'
        bot.reply_to(message, f"✅ تم تعيين وقت الانتهاء إلى {message.text}.\n\n⏱ الآن، أدخل الفاصل الزمني بين المنشورات بالدقائق")
    except ValueError:
        bot.reply_to(message, "❌ تنسيق غير صحيح. الرجاء استخدام HH:MM")

@bot.message_handler(func=lambda message: user_state == 'setting_interval' and is_admin(message))
def process_interval(message):
    try:
        interval = int(message.text)
        if interval <= 0:
            raise ValueError
        
        posting_settings['interval'] = str(interval)
        
        global user_state
        user_state = 'main_menu'
        save_settings()
        bot.reply_to(message, f"✅ تم تعيين الفاصل الزمني إلى {interval} دقيقة", reply_markup=main_keyboard())
    except ValueError:
        bot.reply_to(message, "❌ الرجاء إدخال رقم صحيح موجب")

@bot.message_handler(func=lambda message: message.text == '📊 عرض الإعدادات' and is_admin(message))
def show_settings(message):
    if None in posting_settings.values():
        bot.reply_to(message, "⚠️ لم يتم تعيين جميع الإعدادات بعد. الرجاء استخدام '🔧 تغيير الإعدادات' لإكمال الإعداد.")
    else:
        settings_text = "📊 الإعدادات الحالية:\n\n"
        settings_text += f"🕒 وقت البدء: {posting_settings['start_time']}\n"
        settings_text += f"🕒 وقت الانتهاء: {posting_settings['end_time']}\n"
        settings_text += f"⏱ الفاصل الزمني: {posting_settings['interval']} دقيقة"
        bot.reply_to(message, settings_text)

@bot.message_handler(func=lambda message: message.text == '➕ إضافة محتوى' and is_admin(message))
def add_content(message):
    global user_state
    user_state = 'adding_content'
    bot.reply_to(message, "📤 يمكنك الآن إرسال نص أو صورة أو فيديو لإضافتها إلى قائمة النشر.")

@bot.message_handler(func=lambda message: message.text == '📋 عرض المحتوى' and is_admin(message))
def show_content_list(message):
    if not messages_queue:
        bot.reply_to(message, "📭 قائمة المحتوى فارغة حاليًا.")
    else:
        content_list = "\n".join([f"{msg['type']} - {msg['caption_text']}" for msg in messages_queue])
        bot.reply_to(message, f"📋 قائمة المحتوى:\n\n{content_list}")

@bot.message_handler(func=lambda message: message.text == '🗑 حذف القائمة' and is_admin(message))
def clear_content_list(message):
    global messages_queue
    messages_queue.clear()
    bot.reply_to(message, "🗑 تم حذف قائمة المحتوى.")

@bot.message_handler(func=lambda message: message.text == '➕ إضافة قناة عامة' and is_admin(message))
def add_public_channel(message):
    global user_state
    user_state = 'adding_public_channel'
    bot.reply_to(message, "📡 الرجاء إرسال معرف القناة العامة (بدون @).")

@bot.message_handler(func=lambda message: user_state == 'adding_public_channel' and is_admin(message))
def process_public_channel(message):
    channel_id = message.text.strip()
    if channel_id not in channels['public_channels']:
        channels['public_channels'].append(channel_id)
        save_channels(channels)
        bot.reply_to(message, f"✅ تم إضافة القناة العامة {channel_id} بنجاح.")
    else:
        bot.reply_to(message, "⚠️ القناة العامة موجودة بالفعل.")

@bot.message_handler(func=lambda message: message.text == '➕ إضافة قناة خاصة' and is_admin(message))
def add_private_channel(message):
    global user_state
    user_state = 'adding_private_channel'
    bot.reply_to(message, "📡 الرجاء إرسال معرف القناة الخاصة.")

@bot.message_handler(func=lambda message: user_state == 'adding_private_channel' and is_admin(message))
def process_private_channel(message):
    channel_id = message.text.strip()
    if channel_id not in channels['private_channel_ids']:
        channels['private_channel_ids'].append(channel_id)
        save_channels(channels)
        bot.reply_to(message, f"✅ تم إضافة القناة الخاصة {channel_id} بنجاح.")
    else:
        bot.reply_to(message, "⚠️ القناة الخاصة موجودة بالفعل.")

@bot.message_handler(func=lambda message: message.text == '🗑 إزالة قناة عامة' and is_admin(message))
def remove_public_channel(message):
    global user_state
    user_state = 'removing_public_channel'
    bot.reply_to(message, "📡 الرجاء إرسال معرف القناة العامة (بدون @) لحذفه.")

@bot.message_handler(func=lambda message: user_state == 'removing_public_channel' and is_admin(message))
def process_remove_public_channel(message):
    channel_id = message.text.strip()
    if channel_id in channels['public_channels']:
        channels['public_channels'].remove(channel_id)
        save_channels(channels)
        bot.reply_to(message, f"✅ تم إزالة القناة العامة {channel_id} بنجاح.")
    else:
        bot.reply_to(message, "⚠️ لم يتم العثور على القناة العامة.")

@bot.message_handler(func=lambda message: message.text == '🗑 إزالة قناة خاصة' and is_admin(message))
def remove_private_channel(message):
    global user_state
    user_state = 'removing_private_channel'
    bot.reply_to(message, "📡 الرجاء إرسال معرف القناة الخاصة لحذفه.")

@bot.message_handler(func=lambda message: user_state == 'removing_private_channel' and is_admin(message))
def process_remove_private_channel(message):
    channel_id = message.text.strip()
    if channel_id in channels['private_channel_ids']:
        channels['private_channel_ids'].remove(channel_id)
        save_channels(channels)
        bot.reply_to(message, f"✅ تم إزالة القناة الخاصة {channel_id} بنجاح.")
    else:
        bot.reply_to(message, "⚠️ لم يتم العثور على القناة الخاصة.")

@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_content(message):
    if user_state == 'adding_content' and is_admin(message):
        message_type = 'photo' if message.content_type == 'photo' else 'video' if message.content_type == 'video' else 'text'
        caption_text = message.caption if message.content_type in ['photo', 'video'] else message.text
        
        file_id = message.photo[-1].file_id if message.content_type == 'photo' else message.video.file_id if message.content_type == 'video' else None
        
        messages_queue.append({'type': message_type, 'file_id': file_id, 'caption_text': caption_text})
        bot.reply_to(message, "✅ تم إضافة المحتوى بنجاح إلى قائمة النشر.")

def start_posting_thread():
    thread = threading.Thread(target=publish_message)
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    start_posting_thread()
    bot.polling()
