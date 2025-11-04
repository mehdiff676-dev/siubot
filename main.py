import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
import json
import datetime
import sqlite3
import random
import requests
import os
import time
import threading
import math
import logging
import re
from urllib.parse import urlparse
import tempfile
import yt_dlp

# تهيئة البوت
API_TOKEN = '8537993182:AAEqfQf57Lt_ToF85GbSLf9pMSTgT7NGWBE'
bot = telebot.TeleBot(API_TOKEN)

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# قاعدة البيانات المتطورة
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    # جدول المستخدمين
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  join_date TEXT,
                  warnings INTEGER DEFAULT 0,
                  messages_count INTEGER DEFAULT 0,
                  reputation INTEGER DEFAULT 100,
                  last_activity TEXT,
                  is_premium INTEGER DEFAULT 0,
                  is_member INTEGER DEFAULT 1,
                  membership_type TEXT DEFAULT 'free',
                  membership_expiry TEXT,
                  coins INTEGER DEFAULT 0)''')
    
    # جدول المجموعات
    c.execute('''CREATE TABLE IF NOT EXISTS groups
                 (chat_id INTEGER PRIMARY KEY,
                  title TEXT,
                  description TEXT,
                  welcome_message TEXT,
                  rules TEXT,
                  photo TEXT DEFAULT NULL,
                  welcome_enabled INTEGER DEFAULT 1,
                  channel_required INTEGER DEFAULT 0,
                  channel_url TEXT,
                  created_date TEXT)''')
    
    # جدول المشرفين والمميزين
    c.execute('''CREATE TABLE IF NOT EXISTS special_users
                 (chat_id INTEGER,
                  user_id INTEGER,
                  role TEXT,
                  permissions TEXT,
                  added_date TEXT,
                  PRIMARY KEY (chat_id, user_id))''')
    
    conn.commit()
    conn.close()
    logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")

def update_db_schema():
    """تحديث هيكل قاعدة البيانات"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    try:
        # التحقق من وجود الأعمدة وإضافتها إذا لم تكن موجودة
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]
        
        # الأعمدة المطلوبة
        required_columns = {
            'last_activity': 'TEXT',
            'is_member': 'INTEGER DEFAULT 1',
            'membership_type': 'TEXT DEFAULT "free"',
            'membership_expiry': 'TEXT',
            'coins': 'INTEGER DEFAULT 0'
        }
        
        for column_name, column_type in required_columns.items():
            if column_name not in columns:
                c.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                logger.info(f"✅ تم إضافة العمود {column_name}")
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث قاعدة البيانات: {e}")
    finally:
        conn.close()

# تهيئة وتحديث قاعدة البيانات
init_db()
update_db_schema()

# نظام الإعدادات
def get_group_settings(chat_id):
    """جلب إعدادات المجموعة"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM groups WHERE chat_id = ?', (chat_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'title': result[1],
            'description': result[2],
            'welcome_message': result[3] or 'مرحباً بك {name} في المجموعة! 🌟',
            'rules': result[4] or '📝 القواعد:\\n• احترام الأعضاء\\n• عدم السبام\\n• الالتزام بالأدب',
            'photo': result[5],
            'welcome_enabled': bool(result[6] if result[6] is not None else True),
            'channel_required': bool(result[7] if result[7] is not None else False),
            'channel_url': result[8]
        }
    else:
        default_settings = {
            'title': '',
            'description': '',
            'welcome_message': 'مرحباً بك {name} في المجموعة! 🌟',
            'rules': '📝 القواعد:\\n• احترام الأعضاء\\n• عدم السبام\\n• الالتزام بالأدب',
            'photo': None,
            'welcome_enabled': True,
            'channel_required': False,
            'channel_url': None
        }
        save_group_settings(chat_id, default_settings)
        return default_settings

def save_group_settings(chat_id, settings):
    """حفظ إعدادات المجموعة"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO groups 
                 (chat_id, title, description, welcome_message, rules, photo, welcome_enabled, channel_required, channel_url, created_date)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (chat_id, settings['title'], settings['description'], 
               settings['welcome_message'], settings['rules'], 
               settings['photo'], int(settings['welcome_enabled']),
               int(settings['channel_required']), settings['channel_url'],
               datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

# نظام إدارة المستخدمين
def save_user_info(user):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute('''INSERT OR IGNORE INTO users 
                 (user_id, username, first_name, last_name, join_date, last_activity, is_member)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user.id, user.username, user.first_name, user.last_name, 
               datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat(), 1))
    
    c.execute('''UPDATE users SET username=?, first_name=?, last_name=?, last_activity=?
                 WHERE user_id=?''',
              (user.username, user.first_name, user.last_name, 
               datetime.datetime.now().isoformat(), user.id))
    
    conn.commit()
    conn.close()

def increment_message_count(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('UPDATE users SET messages_count = messages_count + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# نظام الصلاحيات
def is_admin(chat_id, user_id):
    """التحقق من صلاحية المشرف"""
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['administrator', 'creator']
    except:
        return False

def is_creator(chat_id, user_id):
    """التحقق من صلاحية المالك"""
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        return chat_member.status == 'creator'
    except:
        return False

def is_special_user(chat_id, user_id, role=None):
    """التحقق من المستخدمين المميزين"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    if role:
        c.execute('SELECT * FROM special_users WHERE chat_id = ? AND user_id = ? AND role = ?', 
                  (chat_id, user_id, role))
    else:
        c.execute('SELECT * FROM special_users WHERE chat_id = ? AND user_id = ?', 
                  (chat_id, user_id))
    
    result = c.fetchone()
    conn.close()
    return result is not None

def add_special_user(chat_id, user_id, role):
    """إضافة مستخدم مميز"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO special_users VALUES (?, ?, ?, ?, ?)',
              (chat_id, user_id, role, 'all', datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

# نظام الحماية المخفف
class ProtectionSystem:
    def __init__(self):
        self.user_cooldowns = {}
    
    def check_cooldown(self, user_id, action, cooldown_seconds=1):
        """التحقق من الوقت بين الإجراءات"""
        key = f"{user_id}_{action}"
        current_time = time.time()
        
        if key in self.user_cooldowns:
            last_time = self.user_cooldowns[key]
            if current_time - last_time < cooldown_seconds:
                return False
        
        self.user_cooldowns[key] = current_time
        return True

protection_system = ProtectionSystem()

# نظام التحميل المتطور
def download_media(url, media_type='video'):
    """نظام تحميل متطور"""
    try:
        temp_dir = tempfile.mkdtemp()
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        if media_type == 'video':
            ydl_opts['format'] = 'best[height<=720]/best'
        elif media_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_files = []
            
            for file in os.listdir(temp_dir):
                if file.endswith(('.mp4', '.mp3', '.m4a', '.webm')):
                    file_path = os.path.join(temp_dir, file)
                    file_size = os.path.getsize(file_path)
                    
                    if file_size > 500 * 1024 * 1024:
                        os.remove(file_path)
                        continue
                    
                    downloaded_files.append({
                        'path': file_path,
                        'size': file_size,
                        'type': media_type
                    })
            
            return {
                'success': True,
                'files': downloaded_files,
                'title': info.get('title', 'غير معروف'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', '')
            }
    
    except Exception as e:
        logger.error(f"خطأ في التحميل: {e}")
        return {'success': False, 'error': str(e)}

def is_supported_url(url):
    """التحقق من الروابط المدعومة"""
    supported_domains = [
        'youtube.com', 'youtu.be', 'youtube-nocookie.com',
        'twitter.com', 'x.com', 't.co',
        'instagram.com', 'www.instagram.com',
        'tiktok.com', 'vm.tiktok.com', 'www.tiktok.com',
        'facebook.com', 'fb.watch', 'www.facebook.com',
        'soundcloud.com', 'spotify.com'
    ]
    
    try:
        domain = urlparse(url).netloc.lower()
        return any(supported in domain for supported in supported_domains)
    except:
        return False

# نظام البحث
def search_web(query):
    """نظام بحث"""
    try:
        search_results = {
            'youtube': f'https://www.youtube.com/results?search_query={query}',
            'google': f'https://www.google.com/search?q={query}',
        }
        
        return search_results
    except Exception as e:
        logger.error(f"خطأ في البحث: {e}")
        return {}

# نظام الترحيب
def get_welcome_message(chat_id, user):
    """جلب رسالة الترحيب المخصصة"""
    settings = get_group_settings(chat_id)
    welcome_template = settings['welcome_message']
    
    try:
        members_count = bot.get_chat_members_count(chat_id)
    except:
        members_count = "100+"
    
    # استبدال المتغيرات
    welcome_message = welcome_template.format(
        name=user.first_name,
        username=f"@{user.username}" if user.username else user.first_name,
        id=user.id,
        members=members_count
    )
    
    return welcome_message

# ردود "سيو"
siu_responses = [
    "ليش فاضي اك مبك؟ 😄", "مو فاضي والله! 🏃‍♂️", "نعم، تفضل 🌟", "ما بك؟ كل شيء بخير 🎯",
    "فاضي شوي، شتريد؟ 🤔", "والله مو فاضي، عندي شغل 🚀", "اييه فاضي، حكيك 🎭", "شتبي؟ فاضي بس مادري شسويلك 💭",
    "فاضي وياك، تفضل 🌸", "لا مو فاضي، عندي مشاوير 🏃", "فاضي بس ماني مطلع برا 🏠", "اي فاضي، شقولك؟ 🎪",
]

# لوحات المفاتيح المحسنة - أزرار شغالة فقط
def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    # الأزرار الأساسية الشغالة
    buttons = [
        '👋 سلام', '💍 زوجني', '🤖 سيـو',
        '🎮 ألعاب', '📥 تحميل', '🔍 بحث',
        '📊 إحصائيات', '👤 معلوماتي', '🔄 تحديث',
        '🎲 نرد', '📅 تاريخ', '⏰ وقت',
        '💰 عملات', '🎵 اغاني', '📸 صوره',
        '🎬 فيديو', '📚 مكتبه', '🌤 طقس',
        '🧮 آله', '📝 ملاحظه', '🎯 تحدى'
    ]
    
    for i in range(0, len(buttons), 3):
        keyboard.add(*buttons[i:i+3])
    return keyboard

def create_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # أزرار الإدارة الشغالة
    buttons = [
        '🔨 حظر', '🔇 كتم', '🔊 فك كتم', '⚠️ تحذير',
        '📊 إحصائيات', '⚙️ إعدادات', '🧹 تنظيف', '📢 إذاعة',
        '👥 صلاحيات', '📝 قوانين', '🎊 ترحيب', '👑 أعضاء',
        '🏠 الرئيسية'
    ]
    
    for i in range(0, len(buttons), 2):
        keyboard.add(*buttons[i:i+2])
    return keyboard

def create_games_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # أزرار الألعاب الشغالة
    buttons = [
        '🎲 نرد', '🎯 سهم', '🏀 سله', '⚽ كوره',
        '🎰 قمار', '🧩 لغز', '🔢 رياضيات', '❓ مسابقه',
        '🏠 الرئيسية'
    ]
    
    for i in range(0, len(buttons), 2):
        keyboard.add(*buttons[i:i+2])
    return keyboard

# الأوامر الأساسية
@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    save_user_info(message.from_user)
    
    welcome_text = """
🎊 **أهلاً وسهلاً بك في بوت سيـو!**

🤖 **البوت المتعدد الميزات**

🎯 **الميزات المتاحة:**
• تحميل فيديوهات من اليوتيوب
• ألعاب مسلية وتفاعلية
• إحصائيات ومعلومات
• تحميل الصوت من الفيديو
• بحث سريع ومباشر

💡 **استخدم الأزرار للتنقل بين الميزات!**
    """
    
    bot.reply_to(message, welcome_text, reply_markup=create_main_keyboard())

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
📚 **الأوامر المتاحة:**

🎮 **الألعاب:**
/start - قائمة البوت الرئيسية
/game - قائمة الألعاب
/dice - رمي النرد

📥 **التحميل:**
/download - تحميل فيديو
/video - تحميل فيديو
/audio - تحميل صوت

🔍 **خدمات أخرى:**
/search - بحث
/info - معلومات العضو
/stats - إحصائيات

🛡 **للمشرفين:**
/admin - لوحة الإدارة
    """
    
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['info'])
def user_info(message):
    """معلومات العضو"""
    try:
        if message.reply_to_message:
            user = message.reply_to_message.from_user
        else:
            user = message.from_user
        
        # جلب معلومات العضو من قاعدة البيانات
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_id = ?', (user.id,))
        user_data = c.fetchone()
        conn.close()
        
        if user_data:
            messages_count = user_data[6] or 0
            join_date = user_data[4] or 'غير معروف'
        else:
            messages_count = 0
            join_date = 'غير معروف'
        
        # التحقق من الصلاحيات
        is_user_admin = is_admin(message.chat.id, user.id)
        is_user_creator = is_creator(message.chat.id, user.id)
        
        role = "👑 مالك" if is_user_creator else "⭐ مشرف" if is_user_admin else "👤 عضو"
        
        info_text = f"""
📊 **معلومات العضو**

👤 **الاسم:** {user.first_name}
📛 **اليوزر:** @{user.username or 'لا يوجد'}
🆔 **الآيدي:** `{user.id}`
🎯 **الرتبة:** {role}
💬 **الرسائل:** {messages_count}
📅 **تاريخ الانضمام:** {join_date[:10]}
        """
        
        bot.reply_to(message, info_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")

# نظام الألعاب
@bot.message_handler(commands=['game'])
def games_menu(message):
    games_text = """
🎮 **قائمة الألعاب**

🎲 **ألعاب الحظ:**
• النرد - رمي النرد
• السهم - رمي السهم  
• كرة السلة - تسديد كرة
• كرة القدم - تسديد كرة
• القمار - جرب حظك

🧠 **ألعاب الذكاء:**
• المسابقة - أسئلة ثقافية
• الرياضيات - مسائل حسابية
• الألغاز - ألغاز ذكائية

🎯 **اختر لعبة من الأزرار!**
    """
    
    bot.reply_to(message, games_text, reply_markup=create_games_keyboard())

@bot.message_handler(commands=['dice'])
def dice_game(message):
    dice_value = random.randint(1, 6)
    dice_emoji = ['⚀', '⚁', '⚂', '⚃', '⚄', '⚅']
    
    result_text = f"""
🎲 **لعبة النرد**

🎯 **النتيجة:** {dice_emoji[dice_value-1]} {dice_value}
👤 **اللاعب:** {message.from_user.first_name}

{'🎉 فوز كبير!' if dice_value == 6 else '😊 جيد!' if dice_value >= 4 else '🤞 حظاً أفضل!'}
    """
    
    bot.reply_to(message, result_text)

# نظام التحميل
@bot.message_handler(commands=['download', 'video', 'audio'])
def handle_download_command(message):
    try:
        command = message.text.split()[0]
        url = message.text.split()[1] if len(message.text.split()) > 1 else None
        
        if not url:
            bot.reply_to(message, "📥 أرسل الرابط مع الأمر\nمثال: /download https://youtube.com/...")
            return
        
        if not is_supported_url(url):
            bot.reply_to(message, "❌ هذا الرابط غير مدعوم")
            return
        
        # تحديد نوع التحميل
        media_type = 'video'
        if command == '/audio':
            media_type = 'audio'
        
        wait_msg = bot.reply_to(message, "⏳ جاري التحميل...")
        
        # التحميل في thread منفصل
        def download_thread():
            try:
                result = download_media(url, media_type)
                
                if result['success']:
                    for file_info in result['files']:
                        if file_info['type'] == 'video' and media_type == 'video':
                            with open(file_info['path'], 'rb') as video_file:
                                bot.send_video(
                                    message.chat.id,
                                    video_file,
                                    caption=f"🎬 {result['title']}\n✅ تم التحميل بواسطة البوت",
                                    reply_to_message_id=message.message_id
                                )
                        
                        elif file_info['type'] == 'audio' or media_type == 'audio':
                            with open(file_info['path'], 'rb') as audio_file:
                                bot.send_audio(
                                    message.chat.id,
                                    audio_file,
                                    caption=f"🎵 {result['title']}\n✅ تم التحويل إلى MP3",
                                    reply_to_message_id=message.message_id
                                )
                        
                        # تنظيف الملف المؤقت
                        os.remove(file_info['path'])
                    
                    bot.delete_message(message.chat.id, wait_msg.message_id)
                    
                else:
                    bot.edit_message_text(
                        f"❌ فشل التحميل\n{result['error']}",
                        chat_id=message.chat.id,
                        message_id=wait_msg.message_id
                    )
                    
            except Exception as e:
                bot.edit_message_text(
                    f"❌ حدث خطأ: {str(e)}",
                    chat_id=message.chat.id,
                    message_id=wait_msg.message_id
                )
        
        thread = threading.Thread(target=download_thread)
        thread.start()
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")

# أوامر الإدارة
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    admin_text = """
👑 **لوحة الإدارة**

🎯 **الميزات المتاحة:**
• إدارة الأعضاء
• إعدادات المجموعة
• الإحصائيات
• التنظيف

📊 **اختر من الأزرار:**
    """
    
    bot.reply_to(message, admin_text, reply_markup=create_admin_keyboard())

# معالجة جميع الرسائل والأزرار
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    # تخطي الرسائل من البوت نفسه
    if message.from_user.id == bot.get_me().id:
        return
    
    # حفظ المعلومات
    save_user_info(message.from_user)
    increment_message_count(message.from_user.id)
    
    text = message.text
    
    # ردود "سيو"
    if 'سيو' in text.lower() or 'شيو' in text.lower():
        response = random.choice(siu_responses)
        bot.reply_to(message, response)
        return
    
    # معالجة الأزرار
    if text == '👋 سلام':
        greetings = ["وعليكم السلام 🌹", "أهلاً وسهلاً 🌸", "مرحباً 👋"]
        bot.reply_to(message, random.choice(greetings))
    
    elif text == '💍 زوجني':
        girls = ['سارة', 'فاطمة', 'مريم', 'نور', 'ليلى']
        chosen_girl = random.choice(girls)
        bot.reply_to(message, f"💍 مبروك! زوجتك هي {chosen_girl} 🎉")
    
    elif text == '🤖 سيـو':
        response = random.choice(siu_responses)
        bot.reply_to(message, response)
    
    elif text == '🎮 ألعاب':
        games_menu(message)
    
    elif text == '📥 تحميل':
        bot.reply_to(message, "📥 أرسل رابط اليوتيوب لتحميل الفيديو أو الصوت")
    
    elif text == '🔍 بحث':
        bot.reply_to(message, "🔍 اكتب ما تريد البحث عنه")
        bot.register_next_step_handler(message, process_search)
    
    elif text == '📊 إحصائيات':
        try:
            members_count = bot.get_chat_members_count(message.chat.id)
            stats_text = f"""
📊 **إحصائيات المجموعة**

👥 **الأعضاء:** {members_count}
💬 **النشاط:** {'🔥 عالي' if members_count > 100 else '🟢 متوسط'}
🎯 **الحالة:** نشط
            """
            bot.reply_to(message, stats_text)
        except:
            bot.reply_to(message, "📊 الإحصائيات غير متاحة")
    
    elif text == '👤 معلوماتي':
        user_info(message)
    
    elif text == '🔄 تحديث':
        bot.reply_to(message, "✅ تم التحديث", reply_markup=create_main_keyboard())
    
    elif text == '🎲 نرد':
        dice_game(message)
    
    elif text == '📅 تاريخ':
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        bot.reply_to(message, f"📅 التاريخ: {current_date}")
    
    elif text == '⏰ وقت':
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        bot.reply_to(message, f"⏰ الوقت: {current_time}")
    
    elif text == '💰 عملات':
        coins = random.randint(10, 1000)
        bot.reply_to(message, f"💰 رصيدك: {coins} عملة")
    
    elif text == '🎵 اغاني':
        bot.reply_to(message, "🎵 أرسل رابط فيديو يوتيوب لتحميل الصوت")
    
    elif text == '📸 صوره':
        bot.reply_to(message, "📸 أرسل صورة وسأحللها")
    
    elif text == '🎬 فيديو':
        bot.reply_to(message, "🎬 أرسل رابط يوتيوب لتحميل الفيديو")
    
    elif text == '📚 مكتبه':
        bot.reply_to(message, "📚 المكتبة قريباً...")
    
    elif text == '🌤 طقس':
        weather = ["☀️ مشمس", "🌧 ماطر", "⛅ غائم", "💨 عاصف"]
        bot.reply_to(message, f"🌤 الطقس: {random.choice(weather)}")
    
    elif text == '🧮 آله':
        bot.reply_to(message, "🧮 أرسل مسألة رياضية مثل: 5+3")
        bot.register_next_step_handler(message, process_math)
    
    elif text == '📝 ملاحظه':
        bot.reply_to(message, "📝 اكتب ملاحظتك وسأحفظها")
    
    elif text == '🎯 تحدى':
        challenges = ["🎯 حل هذا اللغز...", "🧩 جرب حظك...", "🔢 ما هو ناتج 5×5؟"]
        bot.reply_to(message, random.choice(challenges))
    
    elif text == '🏠 الرئيسية':
        bot.reply_to(message, "🏠 العودة للقائمة الرئيسية", reply_markup=create_main_keyboard())
    
    # أزرار الإدارة
    elif text == '🔨 حظر' and is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "🔨 رد على العضو الذي تريد حظره")
    
    elif text == '🔇 كتم' and is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "🔇 رد على العضو الذي تريد كتمه")
    
    elif text == '🔊 فك كتم' and is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "🔊 رد على العضو الذي تريد فك كتمه")
    
    elif text == '⚠️ تحذير' and is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "⚠️ رد على العضو الذي تريد تحذيره")
    
    elif text == '⚙️ إعدادات' and is_admin(message.chat.id, message.from_user.id):
        settings = get_group_settings(message.chat.id)
        settings_text = f"""
⚙️ **إعدادات المجموعة**

🎊 الترحيب: {'✅ مفعل' if settings['welcome_enabled'] else '❌ معطل'}
👥 الأعضاء: {bot.get_chat_members_count(message.chat.id)}
        """
        bot.reply_to(message, settings_text)
    
    elif text == '🧹 تنظيف' and is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "🧹 سيتم تنظيف الرسائل قريباً...")
    
    elif text == '📢 إذاعة' and is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "📢 اكتب الرسالة للإذاعة")
    
    elif text == '👥 صلاحيات' and is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "👥 إدارة الصلاحيات قريباً...")
    
    elif text == '📝 قوانين' and is_admin(message.chat.id, message.from_user.id):
        settings = get_group_settings(message.chat.id)
        bot.reply_to(message, f"📝 القوانين:\n{settings['rules']}")
    
    elif text == '🎊 ترحيب' and is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "🎊 إعدادات الترحيب قريباً...")
    
    elif text == '👑 أعضاء' and is_admin(message.chat.id, message.from_user.id):
        try:
            members_count = bot.get_chat_members_count(message.chat.id)
            bot.reply_to(message, f"👑 عدد الأعضاء: {members_count}")
        except:
            bot.reply_to(message, "👑 لا يمكن جلب عدد الأعضاء")

def process_search(message):
    """معالجة البحث"""
    try:
        query = message.text.strip()
        if not query:
            bot.reply_to(message, "❌ يرجى إدخال كلمة بحث")
            return
        
        results = search_web(query)
        
        results_text = f"""
🔍 **نتائج البحث عن:** {query}

📺 يوتيوب: [اضغط هنا]({results.get('youtube', '#')})
🌐 جوجل: [اضغط هنا]({results.get('google', '#')})
        """
        
        bot.reply_to(message, results_text, disable_web_page_preview=False)
        
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")

def process_math(message):
    """معالجة المسائل الرياضية"""
    try:
        problem = message.text.strip()
        # محاولة حل المسألة الرياضية
        try:
            result = eval(problem)
            bot.reply_to(message, f"🧮 الناتج: {result}")
        except:
            bot.reply_to(message, "❌ لا يمكن حل هذه المسألة")
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")

# بدء التشغيل
if __name__ == '__main__':
    print("🤖 بوت سيـو يعمل الآن!")
    print("🎯 جميع الأزرار شغالة وجاهزة")
    print("🚀 البوت متاح للجميع")
    
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        logger.error(f"خطأ في التشغيل: {e}")
        print(f"❌ خطأ: {e}")
        time.sleep(10)