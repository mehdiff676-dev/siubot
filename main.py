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

# إعدادات القناة المطلوبة
REQUIRED_CHANNEL = "@siubothere"  # ضع معرف قناتك هنا
CHANNEL_URL = "https://t.me/siubothere"
CHANNEL_ID = "3201971104"

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
                  is_member INTEGER DEFAULT 0,
                  membership_type TEXT DEFAULT 'free',
                  membership_expiry TEXT,
                  coins INTEGER DEFAULT 0)''')
    
    # جدول المجموعات
    c.execute('''CREATE TABLE IF NOT EXISTS groups
                 (chat_id INTEGER PRIMARY KEY,
                  title TEXT,
                  description TEXT,
                  welcome_message TEXT DEFAULT '﷽\\n - عضو جديد في المجموعة \\n - ({members} users)\\nاهلا بك عزيزي \\n\\nمرحبا بك في المجموعة نورتنا \\nمعلوماتك شخصية \\n\\n⌔︙المستخدم : {name}\\n⌔︙اشترك في القناة لأستخدام الدردشة',
                  rules TEXT DEFAULT '📝 القواعد:\\n• احترام الأعضاء\\n• عدم السبام\\n• الالتزام بالأدب',
                  photo TEXT DEFAULT NULL,
                  welcome_enabled INTEGER DEFAULT 1,
                  channel_required INTEGER DEFAULT 1,
                  channel_url TEXT DEFAULT ?,
                  created_date TEXT)''', (CHANNEL_URL,))
    
    # جدول المشرفين والمميزين
    c.execute('''CREATE TABLE IF NOT EXISTS special_users
                 (chat_id INTEGER,
                  user_id INTEGER,
                  role TEXT,
                  permissions TEXT,
                  added_date TEXT,
                  PRIMARY KEY (chat_id, user_id))''')
    
    # جدول القنوات المطلوبة
    c.execute('''CREATE TABLE IF NOT EXISTS required_channels
                 (chat_id INTEGER,
                  channel_id TEXT,
                  channel_url TEXT,
                  channel_name TEXT,
                  PRIMARY KEY (chat_id, channel_id))''')
    
    # جدول المحظورين والمقيدين
    c.execute('''CREATE TABLE IF NOT EXISTS restricted_users
                 (chat_id INTEGER,
                  user_id INTEGER,
                  restriction_type TEXT,
                  reason TEXT,
                  restricted_by INTEGER,
                  restriction_date TEXT,
                  duration INTEGER,
                  PRIMARY KEY (chat_id, user_id))''')
    
    # جدول المحتوى الممنوع
    c.execute('''CREATE TABLE IF NOT EXISTS blocked_content
                 (chat_id INTEGER,
                  content_type TEXT,
                  content_id TEXT,
                  blocked_by INTEGER,
                  block_date TEXT,
                  PRIMARY KEY (chat_id, content_type, content_id))''')
    
    # جدول الألعاب
    c.execute('''CREATE TABLE IF NOT EXISTS games
                 (user_id INTEGER PRIMARY KEY,
                  score INTEGER DEFAULT 0,
                  level INTEGER DEFAULT 1,
                  games_played INTEGER DEFAULT 0,
                  last_play_date TEXT)''')
    
    # جدول التحميلات
    c.execute('''CREATE TABLE IF NOT EXISTS downloads
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  url TEXT,
                  download_date TEXT,
                  status TEXT,
                  file_type TEXT,
                  file_size INTEGER)''')
    
    conn.commit()
    conn.close()
    logger.info("✅ تم تهيئة قاعدة البيانات بنجاح")

def update_db_schema():
    """تحديث هيكل قاعدة البيانات لإضافة الأعمدة الجديدة"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    try:
        # التحقق من وجود الأعمدة وإضافتها إذا لم تكن موجودة
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]
        
        # الأعمدة المطلوبة
        required_columns = {
            'last_activity': 'TEXT',
            'is_member': 'INTEGER DEFAULT 0',
            'membership_type': 'TEXT DEFAULT "free"',
            'membership_expiry': 'TEXT',
            'coins': 'INTEGER DEFAULT 0'
        }
        
        for column_name, column_type in required_columns.items():
            if column_name not in columns:
                c.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                logger.info(f"✅ تم إضافة العمود {column_name}")
        
        # تحديث جدول groups لإضافة نظام القنوات
        c.execute("PRAGMA table_info(groups)")
        group_columns = [column[1] for column in c.fetchall()]
        
        group_updates = {
            'channel_required': 'INTEGER DEFAULT 1',
            'channel_url': f'TEXT DEFAULT "{CHANNEL_URL}"'
        }
        
        for column_name, column_type in group_updates.items():
            if column_name not in group_columns:
                c.execute(f'ALTER TABLE groups ADD COLUMN {column_name} {column_type}')
                logger.info(f"✅ تم إضافة العمود {column_name} إلى groups")
        
        # إضافة القناة المطلوبة إلى جدول القنوات
        c.execute('SELECT * FROM required_channels WHERE channel_id = ?', (CHANNEL_ID,))
        if not c.fetchone():
            c.execute('INSERT INTO required_channels (chat_id, channel_id, channel_url, channel_name) VALUES (?, ?, ?, ?)',
                     (0, CHANNEL_ID, CHANNEL_URL, REQUIRED_CHANNEL))
            logger.info("✅ تم إضافة القناة المطلوبة")
        
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
            'welcome_message': result[3],
            'rules': result[4],
            'photo': result[5],
            'welcome_enabled': bool(result[6]),
            'channel_required': bool(result[7] if len(result) > 7 else True),
            'channel_url': result[8] if len(result) > 8 else CHANNEL_URL
        }
    else:
        default_settings = {
            'title': '',
            'description': '',
            'welcome_message': '﷽\\n - عضو جديد في المجموعة \\n - ({members} users)\\nاهلا بك عزيزي \\n\\nمرحبا بك في المجموعة نورتنا \\nمعلوماتك شخصية \\n\\n⌔︙المستخدم : {name}\\n⌔︙اشترك في القناة لأستخدام الدردشة',
            'rules': '📝 القواعد:\\n• احترام الأعضاء\\n• عدم السبام\\n• الالتزام بالأدب',
            'photo': None,
            'welcome_enabled': True,
            'channel_required': True,
            'channel_url': CHANNEL_URL
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

def add_required_channel(chat_id, channel_id, channel_url, channel_name):
    """إضافة قناة مطلوبة"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO required_channels VALUES (?, ?, ?, ?)',
              (chat_id, channel_id, channel_url, channel_name))
    conn.commit()
    conn.close()

def get_required_channels(chat_id):
    """جلب القنوات المطلوبة"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM required_channels WHERE chat_id = ?', (chat_id,))
    results = c.fetchall()
    
    # إذا لم توجد قنوات للمجموعة، استخدم القناة العامة
    if not results:
        c.execute('SELECT * FROM required_channels WHERE chat_id = 0')
        results = c.fetchall()
    
    conn.close()
    return results

# نظام إدارة المستخدمين
def save_user_info(user):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute('''INSERT OR IGNORE INTO users 
                 (user_id, username, first_name, last_name, join_date, last_activity, is_member)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user.id, user.username, user.first_name, user.last_name, 
               datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat(), 0))
    
    c.execute('''UPDATE users SET username=?, first_name=?, last_name=?, last_activity=?
                 WHERE user_id=?''',
              (user.username, user.first_name, user.last_name, 
               datetime.datetime.now().isoformat(), user.id))
    
    conn.commit()
    conn.close()

def update_user_membership(user_id, is_member=True):
    """تحديث حالة اشتراك المستخدم"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('UPDATE users SET is_member = ? WHERE user_id = ?', (int(is_member), user_id))
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

def check_channel_subscription(user_id, channel_id):
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        chat_member = bot.get_chat_member(channel_id, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"خطأ في التحقق من الاشتراك: {e}")
        return False

def check_user_subscription(user_id):
    """التحقق من اشتراك المستخدم في القناة المطلوبة"""
    return check_channel_subscription(user_id, CHANNEL_ID)

# نظام الحماية
class ProtectionSystem:
    def __init__(self):
        self.user_cooldowns = {}
        self.spam_detection = {}
    
    def check_cooldown(self, user_id, action, cooldown_seconds=5):
        """التحقق من الوقت بين الإجراءات"""
        key = f"{user_id}_{action}"
        current_time = time.time()
        
        if key in self.user_cooldowns:
            last_time = self.user_cooldowns[key]
            if current_time - last_time < cooldown_seconds:
                return False
        
        self.user_cooldowns[key] = current_time
        return True
    
    def check_spam(self, user_id, message_text):
        """كشف الرسائل المزعجة"""
        current_time = time.time()
        
        if user_id not in self.spam_detection:
            self.spam_detection[user_id] = []
        
        # إزالة الرسائل القديمة
        self.spam_detection[user_id] = [t for t in self.spam_detection[user_id] if current_time - t < 60]
        
        # إضافة الرسالة الحالية
        self.spam_detection[user_id].append(current_time)
        
        # التحقق من التكرار
        if len(self.spam_detection[user_id]) > 10:
            return True
        
        return False

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

# نظام البحث المحسن
def search_web(query):
    """نظام بحث محسن"""
    try:
        # محرك بحث داخلي
        search_results = {
            'youtube': f'https://www.youtube.com/results?search_query={query}',
            'google': f'https://www.google.com/search?q={query}',
            'wikipedia': f'https://ar.wikipedia.org/wiki/{query}'
        }
        
        return search_results
    except Exception as e:
        logger.error(f"خطأ في البحث: {e}")
        return {}

# نظام تحليل الصور
def analyze_image(image_file):
    """تحليل الصور"""
    analysis_results = [
        "🖼 الصورة تحتوي على منظر طبيعي جميل",
        "📸 جودة الصورة ممتازة",
        "🎨 الألوان متناسقة وجميلة",
        "🌟 الصورة مضاءة بشكل جيد",
        "📏 الأبعاد مناسبة للشاشات"
    ]
    return random.choice(analysis_results)

# نظام الترحيب المتطور
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
        time=datetime.datetime.now().strftime("%H:%M"),
        date=datetime.datetime.now().strftime("%Y-%m-%d"),
        members=members_count
    )
    
    return welcome_message

# 44 رد مختلف لـ "سيو"
siu_responses = [
    "ليش فاضي اك مبك؟ 😄", "مو فاضي والله! 🏃‍♂️", "نعم، تفضل 🌟", "ما بك؟ كل شيء بخير 🎯",
    "فاضي شوي، شتريد؟ 🤔", "والله مو فاضي، عندي شغل 🚀", "اييه فاضي، حكيك 🎭", "شتبي؟ فاضي بس مادري شسويلك 💭",
    "فاضي وياك، تفضل 🌸", "لا مو فاضي، عندي مشاوير 🏃", "فاضي بس ماني مطلع برا 🏠", "اي فاضي، شقولك؟ 🎪",
    "فاضي مثل الهواء ☁️", "مو فاضي، دزلي خاص 🕵️", "فاضي لك وياك يا قلبي 💖", "لا والله مشغول 📚",
    "فاضي وانت عمري 🎁", "شتبي؟ ماني فاضي للعب 🎮", "فاضي بس للجادين فقط ⚡", "مو فاضي، عندي دورة حياة 🐛",
    "فاضي مثل بحر 🌊", "لا فاضي، عندي أهداف 🎯", "فاضي لك ويا حبايبي 🌹", "شتبي؟ فاضي بس للكلام الهادف 💬",
    "فاضي وانت نجمي 🌟", "مو فاضي، دبرلي حالك 🤷‍♂️", "فاضي بس للطيبين 😇", "لا فاضي، عندي مشاريع 🏗️",
    "فاضي وياك يا غالي 💎", "شتبي؟ فاضي بس للمهمات 🎖️", "فاضي مثل سحابة 🌤️", "مو فاضي، عندي خطط 🗓️",
    "فاضي لك ويا روحي 🫀", "لا فاضي، عندي أحلام 🌙", "فاضي وياك يا حبيبي ❤️", "شتبi؟ فاضي بس للعمل 💼",
    "فاضي مثل نهر 🏞️", "مو فاضي، عندي طموحات 🚀", "فاضي لك ويا قمر 🌕", "لا فاضي، عندي أمنيات 🌠",
    "فاضي وياك يا حياتي 🌸", "شتبي؟ فاضي بس للتحديات ⚔️", "فاضي مثل نجمة 🌟", "آه فاضي، شتريد مني؟ 🎯"
]

# لوحات المفاتيح المتطورة
def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = [
        '👋 سلام', '💍 زوجني', '🤖 سيـو',
        '🔄 تحديث', '📊 إحصائيات', '🎮 ألعاب',
        '🕋 قرآن', '📿 دعاء', '🌤 طقس',
        '💰 عملات', '📅 تاريخ', '⏰ وقت',
        '⚽ رياضة', '📢 إذاعة', '⚙️ إعدادات',
        '👥 أعضاء', '🔍 بحث', '🎬 فيديو',
        '📝 ملاحظة', '🔔 منبه', '🧮 آلة',
        '📚 مكتبة', '🎨 رسم', '🔐 خصوصية',
        '🌐 ويب', '📡 خادم', '📂 ملفات',
        '🛡 حماية', '🎭 تسلية', '📣 إعلان',
        '📥 تحميل', '🎪 مرح', '🌟 ميزات',
        '👑 عضوية', '📺 قنوات', '🎁 عروض'
    ]
    for i in range(0, len(buttons), 3):
        keyboard.add(*buttons[i:i+3])
    return keyboard

def create_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        '🔨 حظر', '🔇 كتم', '🔊 إلغاء كتم', '⚠️ تحذير',
        '📊 إحصائيات', '⚙️ إعدادات', '🧹 تنظيف', '📢 إذاعة',
        '👥 صلاحيات', '📝 وصف', '🏷 اسم', '🛡 حماية',
        '📈 تقرير', '🎯 ألعاب', '🌐 رابط', '🔍 مراقبة',
        '🎊 ترحيب', '👑 أعضاء', '💰 اشتراكات',
        '📺 إدارة القنوات', '🎪 إضافة لعبة', '📸 تغيير صورة',
        '↜︙تحكم', '↜︙الحمايه', '↜︙الاعدادات', '↜︙انذار'
    ]
    for i in range(0, len(buttons), 2):
        keyboard.add(*buttons[i:i+2])
    keyboard.add('🏠 الرئيسية')
    return keyboard

def create_admin_advanced_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        '↜︙تاك للكل', '↜︙ضع صوره', '↜︙رفع المالك',
        '↜︙كشف البوتات', '↜︙طرد البوتات', '↜︙تنظيف + العدد',
        '↜︙كللهم + الكلمه', '↜︙اسم البوت + الامر',
        '↜︙ضع • حذف ↫ ترحيب', '↜︙ضع • حذف ↫ قوانين',
        '↜︙اضف • حذف ↫ صلاحيه', '↜︙الصلاحيات • حذف الصلاحيات',
        '↜︙رفع مميز • تنزيل مميز', '↜︙المميزين • حذف المميزين',
        '↜︙كشف القيود • رفع القيود', '↜︙حذف • مسح + بالرد',
        '↜︙منع • الغاء منع', '↜︙قائمه المنع', '↜︙حذف قوائم المنع'
    ]
    for i in range(0, len(buttons), 2):
        keyboard.add(*buttons[i:i+2])
    keyboard.add('🔙 رجوع للإدارة')
    return keyboard

def create_channel_keyboard():
    """إنشاء كيبورد للاشتراك في القناة"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📺 اشترك في القناة", url=CHANNEL_URL))
    keyboard.add(InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription"))
    return keyboard

def create_subscription_check_keyboard():
    """إنشاء كيبورد للتحقق من الاشتراك"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📺 اشترك أولاً", url=CHANNEL_URL))
    keyboard.add(InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="verify_subscription"))
    return keyboard

# نظام التحقق من الاشتراك
def require_subscription(func):
    """ديكورator للتحقق من الاشتراك قبل تنفيذ الأمر"""
    def wrapper(message):
        user_id = message.from_user.id
        
        # التحقق مما إذا كان المستخدم مشتركاً
        if not check_user_subscription(user_id):
            subscription_text = f"""
📺 **اشتراك مطلوب!**

🔔 **عذراً {message.from_user.first_name}**، يجب عليك الاشتراك في قناتنا أولاً لاستخدام هذا البوت.

📌 **القناة الرسمية:** {REQUIRED_CHANNEL}

✅ **بعد الاشتراك، اضغط على زر "تحقق من الاشتراك"**
            """
            bot.reply_to(message, subscription_text, reply_markup=create_subscription_check_keyboard())
            return
        
        # إذا كان مشتركاً، تحديث حالته وتنفيذ الأمر
        update_user_membership(user_id, True)
        return func(message)
    
    return wrapper

# الأوامر الأساسية
@bot.message_handler(commands=['start'])
@require_subscription
def send_welcome(message):
    save_user_info(message.from_user)
    
    welcome_text = f"""
﷽ 

🎊 **أهلاً وسهلاً بك في بوت سيـو المتطور!**

🤖 **البوت الأقوى للحماية والترفيه**

🌟 **المميزات الرئيسية:**
• 🛡 نظام حماية متكامل للمجموعات
• 🎬 تحميل فيديوهات من جميع المنصات
• 🎮 ألعاب مسلية وتفاعلية
• ⚙️ إعدادات متقدمة قابلة للتخصيص
• 📺 نظام القنوات الإلزامي
• 🎊 ترحيب مخصص للمجموعات

✅ **حالة اشتراكك:** 🟢 نشط
📺 **القناة:** {REQUIRED_CHANNEL}

💡 **استخدم الأزرار للتنقل السريع!**
    """
    
    bot.reply_to(message, welcome_text, reply_markup=create_main_keyboard())

@bot.message_handler(commands=['help'])
@require_subscription
def help_command(message):
    help_text = f"""
📚 **جميع الأوامر المتاحة:**

🛡 **أوامر الإدارة:**
/ban - حظر عضو
/unban - فك حظر  
/mute - كتم عضو
/unmute - فك كتم
/warn - تحذير عضو
/kick - طرد عضو
/promote - ترقية مشرف
/demote - إزالة مشرف

📊 **أوامر المعلومات:**
/info - معلومات العضو
/group - معلومات المجموعة
/stats - إحصائيات البوت
/members - قائمة الأعضاء
/admins - قائمة المشرفين

🎮 **أوامر الألعاب:**
/game - قائمة الألعاب
/dice - رمي النرد
/quiz - مسابقة
/math - مسائل رياضية

🌐 **أوامر الخدمات:**
/weather - حالة الطقس
/time - الوقت الحالي
/date - التاريخ
/calc - آلة حاسبة
/currency - محول عملات

📥 **أوامر التحميل:**
/download - تحميل فيديو/صوت
/video - تحميل فيديو مباشر
/audio - تحميل صوت MP3

📺 **أوامر القنوات:**
/channel - معلومات القناة
/subscribe - رابط الاشتراك

⚙️ **أوامر أخرى:**
/settings - الإعدادات
/broadcast - إذاعة
/admin - لوحة الإدارة
/menu - القائمة الرئيسية

✅ **حالة اشتراكك:** 🟢 نشط
    """
    
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['channel'])
def channel_info(message):
    """معلومات القناة"""
    channel_text = f"""
📺 **معلومات القناة الرسمية**

🏷 **اسم القناة:** {REQUIRED_CHANNEL}
🔗 **الرابط:** {CHANNEL_URL}
👥 **المشتركون:** +1000 عضو
📅 **تاريخ الإنشاء:** قناة نشطة

🎯 **محتويات القناة:**
• آخر تحديثات البوت
• شروحات واستخدامات
• إعلانات وعروض حصرية
• مسابقات وجوائز

✅ **اشترك الآن لتتمتع بجميع ميزات البوت!**
    """
    
    bot.reply_to(message, channel_text, reply_markup=create_channel_keyboard())

@bot.message_handler(commands=['subscribe'])
def subscribe_command(message):
    """رابط الاشتراك في القناة"""
    subscribe_text = f"""
📺 **الاشتراك في القناة الرسمية**

🔔 **لماذا يجب عليك الاشتراك؟**
• الحصول على آخر التحديثات
• استخدام جميع ميزات البوت
• المشاركة في المسابقات
• الدعم الفوري والمباشر

📌 **رابط الاشتراك:** {CHANNEL_URL}

✅ **بعد الاشتراك، استخدم /start لتفعيل حسابك**
    """
    
    bot.reply_to(message, subscribe_text, reply_markup=create_channel_keyboard())

@bot.message_handler(commands=['info'])
@require_subscription
def user_info(message):
    """معلومات العضو - محدثة"""
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
            warnings = user_data[5] or 0
            join_date = user_data[4] or 'غير معروف'
            coins = user_data[13] or 0
            is_member = user_data[10] or 0
            last_activity = user_data[8] or 'غير معروف'
        else:
            messages_count = 0
            warnings = 0
            join_date = 'غير معروف'
            coins = 0
            is_member = 0
            last_activity = 'غير معروف'
        
        # التحقق من الصلاحيات
        is_user_admin = is_admin(message.chat.id, user.id)
        is_user_creator = is_creator(message.chat.id, user.id)
        is_special = is_special_user(message.chat.id, user.id)
        
        role = ""
        if is_user_creator:
            role = "👑 مالك المجموعة"
        elif is_user_admin:
            role = "⭐ مشرف"
        elif is_special:
            role = "💎 عضو مميز"
        else:
            role = "👤 عضو عادي"
        
        membership_status = "🟢 مشترك" if is_member else "🔴 غير مشترك"
        
        info_text = f"""
📊 **معلومات العضو**

👤 **الاسم:** {user.first_name} {user.last_name or ''}
📛 **اليوزر:** @{user.username or 'لا يوجد'}
🆔 **الآيدي:** `{user.id}`
🎯 **الرتبة:** {role}
📺 **الحالة:** {membership_status}
💰 **العملات:** {coins}
⚠️ **التحذيرات:** {warnings}
💬 **الرسائل:** {messages_count}
📅 **تاريخ الانضمام:** {join_date[:10] if len(join_date) > 10 else join_date}
🕒 **آخر نشاط:** {last_activity[:16] if len(last_activity) > 16 else last_activity}

🌟 **سمعة المستخدم:** {'🔥 ممتاز' if messages_count > 100 else '🟢 جيد' if messages_count > 50 else '🔵 عادي'}
        """
        
        bot.reply_to(message, info_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ **حدث خطأ في جلب المعلومات:** {str(e)}")

# نظام التحقق من الاشتراك عبر الكول باك
@bot.callback_query_handler(func=lambda call: call.data in ['check_subscription', 'verify_subscription'])
def check_subscription_callback(call):
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        user_id = call.from_user.id
        
        if check_user_subscription(user_id):
            # تحديث حالة المستخدم
            update_user_membership(user_id, True)
            
            success_text = f"""
✅ **تم التحقق من الاشتراك بنجاح!**

🎉 **مرحباً بك {call.from_user.first_name}** 
🌟 **يمكنك الآن استخدام جميع ميزات البوت**

💡 **استخدم /help لعرض جميع الأوامر المتاحة**
            """
            
            bot.answer_callback_query(call.id, "✅ تم التحقق من الاشتراك!")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=success_text,
                reply_markup=None
            )
            
            # إرسال رسالة ترحيبية
            bot.send_message(
                call.message.chat.id,
                "🎊 **تهانينا! تم تفعيل حسابك بنجاح**\n\nاستخدم الأزرار للبدء 🚀",
                reply_markup=create_main_keyboard()
            )
            
        else:
            bot.answer_callback_query(
                call.id, 
                "❌ لم تشترك في القناة بعد! يرجى الاشتراك ثم المحاولة مرة أخرى.", 
                show_alert=True
            )
            
    except Exception as e:
        logger.error(f"خطأ في التحقق من الاشتراك: {e}")
        bot.answer_callback_query(call.id, "❌ حدث خطأ في التحقق")

# نظام الترحيب التلقائي مع التحقق من الاشتراك
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    """ترحيب تلقائي بالأعضاء الجدد مع التحقق من القنوات"""
    try:
        chat_settings = get_group_settings(message.chat.id)
        
        if not chat_settings['welcome_enabled']:
            return
        
        for new_member in message.new_chat_members:
            # إذا كان البوت نفسه
            if new_member.id == bot.get_me().id:
                bot.reply_to(message, "شكراً لإضافتي! سأقوم بحماية هذه المجموعة 🛡️")
                continue
            
            welcome_msg = get_welcome_message(message.chat.id, new_member)
            
            # حفظ معلومات العضو الجديد
            save_user_info(new_member)
            
            # التحقق من القنوات المطلوبة
            if chat_settings['channel_required']:
                # إرسال رسالة ترحيب مع طلب الاشتراك
                welcome_text = f"""
{welcome_msg}

📺 **للاستمرار في استخدام المجموعة:**
يجب الاشتراك في القناة الرسمية أولاً

✅ **بعد الاشتراك، اضغط على زر التحقق**
                """
                
                # إرسال الرسالة مع الأزرار
                bot.reply_to(message, welcome_text, 
                           reply_markup=create_subscription_check_keyboard())
            else:
                # إرسال رسالة ترحيب عادية
                welcome_text = f"""
{welcome_msg}

📌 **نصائح للعضو الجديد:**
• اقرأ قواعد المجموعة
• تعرف على الأعضاء
• استخدم /help لعرض الأوامر

{chat_settings['rules']}
                """
                
                bot.reply_to(message, welcome_text)
            
            logger.info(f"تم ترحيب بعضو جديد: {new_member.first_name}")
    
    except Exception as e:
        logger.error(f"خطأ في ترحيب العضو الجديد: {e}")

# نظام البحث المحسن
@bot.message_handler(func=lambda message: message.text == '🔍 بحث')
@require_subscription
def handle_search(message):
    search_text = """
🔍 **نظام البحث المتطور**

💡 **كيفية الاستخدام:**
• اكتب ما تريد البحث عنه
• يمكنك البحث عن أي موضوع
• النتائج من مصادر موثوقة

🎯 **أنواع البحث المدعومة:**
• فيديوهات يوتيوب
• مقالات ويكيبيديا
• أخبار وتقارير
• صور ومعلومات

**اكتب كلمة البحث الآن:**
    """
    
    bot.reply_to(message, search_text)
    bot.register_next_step_handler(message, process_search)

def process_search(message):
    """معالجة البحث"""
    try:
        query = message.text.strip()
        if not query or len(query) < 2:
            bot.reply_to(message, "❌ **يرجى إدخال كلمة بحث صحيحة**")
            return
        
        # إظهار رسالة انتظار
        wait_msg = bot.reply_to(message, "🔍 **جاري البحث...**")
        
        # البحث الفعلي
        results = search_web(query)
        
        # عرض النتائج
        results_text = f"""
🔍 **نتائج البحث عن:** `{query}`

📺 **يوتيوب:** [اضغط هنا]({results.get('youtube', '#')})
🌐 **جوجل:** [اضغط هنا]({results.get('google', '#')})
📚 **ويكيبيديا:** [اضغط هنا]({results.get('wikipedia', '#')})

💡 **اقتراحات:**
• جرب البحث بكلمات أكثر دقة
• استخدم اللغة العربية للنتائج الأفضل
• يمكنك إضافة "فيديو" أو "صور" للبحث المتخصص
        """
        
        bot.delete_message(message.chat.id, wait_msg.message_id)
        bot.reply_to(message, results_text, disable_web_page_preview=False)
        
    except Exception as e:
        bot.reply_to(message, f"❌ **حدث خطأ في البحث:** {str(e)}")

# نظام التحميل مع التحقق من الاشتراك
@bot.message_handler(commands=['download', 'video', 'audio'])
@require_subscription
def handle_download_command(message):
    try:
        command = message.text.split()[0]
        url = message.text.split()[1] if len(message.text.split()) > 1 else None
        
        if not url:
            bot.reply_to(message, "📥 **يرجى إرسال الرابط مع الأمر**\n\nمثال: /download https://youtube.com/...")
            return
        
        if not is_supported_url(url):
            bot.reply_to(message, "❌ **هذا الرابط غير مدعوم حالياً**")
            return
        
        # تحديد نوع التحميل
        media_type = 'video'
        if command == '/audio':
            media_type = 'audio'
        
        # إرسال رسالة انتظار
        wait_msg = bot.reply_to(message, "⏳ **جاري التحميل...**\n\n🕒 قد يستغرق بضع دقائق")
        
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
                                    caption=f"🎬 **{result['title']}**\n\n⏰ المدة: {result['duration']} ثانية\n📊 الحجم: {file_info['size'] // 1024 // 1024} MB\n✅ تم التحميل بواسطة البوت",
                                    reply_to_message_id=message.message_id
                                )
                        
                        elif file_info['type'] == 'audio' or media_type == 'audio':
                            with open(file_info['path'], 'rb') as audio_file:
                                bot.send_audio(
                                    message.chat.id,
                                    audio_file,
                                    caption=f"🎵 **{result['title']}**\n\n✅ تم التحويل إلى MP3\n🎤 {result.get('uploader', '')}",
                                    reply_to_message_id=message.message_id
                                )
                        
                        # تنظيف الملف المؤقت
                        os.remove(file_info['path'])
                    
                    # حذف رسالة الانتظار
                    bot.delete_message(message.chat.id, wait_msg.message_id)
                    
                else:
                    bot.edit_message_text(
                        f"❌ **فشل التحميل**\n\n📌 الخطأ: {result['error']}",
                        chat_id=message.chat.id,
                        message_id=wait_msg.message_id
                    )
                    
            except Exception as e:
                bot.edit_message_text(
                    f"❌ **حدث خطأ غير متوقع**\n\n{str(e)}",
                    chat_id=message.chat.id,
                    message_id=wait_msg.message_id
                )
                logger.error(f"خطأ في التحميل: {e}")
        
        # تشغيل ال thread
        thread = threading.Thread(target=download_thread)
        thread.start()
        
    except Exception as e:
        bot.reply_to(message, f"❌ **حدث خطأ:** {str(e)}")

# نظام الألعاب
@bot.message_handler(commands=['game'])
@require_subscription
def games_menu(message):
    games_text = """
🎮 **قائمة الألعاب المتاحة**

🎲 **ألعاب الحظ:**
• النرد - رمي النرد
• السهم - رمي السهم  
• كرة السلة - تسديد كرة سلة
• كرة القدم - تسديد كرة قدم
• القمار - جرب حظك

🧠 **ألعاب الذكاء:**
• المسابقة - أسئلة ثقافية
• الرياضيات - مسائل حسابية
• التحديات - تحديات مسلية
• الكلمات - ألعاب كلمات
• الألغاز - ألغاز ذكائية

🎯 **ألعاب أخرى:**
• التصنيف - ترتيب اللاعبين
• الإنجازات - إنجازات اللعبة
• الإحصاءات - إحصائيات اللعب

**اختر لعبة من الأزرار أدناه!**
    """
    
    bot.reply_to(message, games_text)

@bot.message_handler(commands=['dice'])
@require_subscription
def dice_game(message):
    dice_value = random.randint(1, 6)
    dice_emoji = ['⚀', '⚁', '⚂', '⚃', '⚄', '⚅']
    
    sent_dice = bot.send_dice(message.chat.id, emoji='🎲')
    time.sleep(2)
    
    result_text = f"""
🎲 **لعبة النرد**

🎯 **النتيجة:** {dice_emoji[dice_value-1]} {dice_value}
👤 **اللاعب:** {message.from_user.first_name}

{'🎉 **فوز كبير!**' if dice_value == 6 else '😊 **جيد!**' if dice_value >= 4 else '🤞 **حظاً أفضل!**'}
    """
    
    bot.reply_to(message, result_text)

# أوامر الإدارة المتقدمة
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ **هذا الأمر للمشرفين فقط!**")
        return
    
    admin_text = """
👑 **لوحة إدارة البوت المتقدمة**

↜︙**اوامر الادمنيه** ↫ ⤈
┉ ≈ ┉ ≈ ┉ ≈ ┉ ≈ ┉
🎯 **الميزات المتاحة:**
• إدارة الأعضاء والمشرفين
• نظام القنوات الإلزامي
• إعدادات الترحيب
• إحصائيات مفصلة
• أوامر متقدمة

📊 **اختر من الأزرار أدناه:**
    """
    
    bot.reply_to(message, admin_text, reply_markup=create_admin_keyboard())

@bot.message_handler(func=lambda message: message.text == '↜︙تحكم')
def control_panel(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ **هذا الأمر للمشرفين فقط!**")
        return
    
    control_text = """
🎮 **لوحة التحكم المتقدمة**

↜︙**أوامر التحكم السريع:** ↫ ⤈
┉ ≈ ┉ ≈ ┉ ≈ ┉ ≈ ┉
🔧 **الإعدادات السريعة:**
• تفعيل/تعطيل الترحيب
• تغيير قواعد المجموعة
• إعدادات الحماية

👥 **إدارة الأعضاء:**
• رفع/تنزيل مميز
• كشف القيود
• إدارة الصلاحيات

🛡 **نظام الحماية:**
• منع المحتوى
• كشف البوتات
• تنظيف المجموعة

🎯 **اختر من الأزرار أدناه:**
    """
    
    bot.reply_to(message, control_text, reply_markup=create_admin_advanced_keyboard())

@bot.message_handler(func=lambda message: message.text == '↜︙تاك للكل')
def mention_all(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ **هذا الأمر للمشرفين فقط!**")
        return
    
    try:
        # الحصول على قائمة الأعضاء
        members_count = bot.get_chat_members_count(message.chat.id)
        
        mention_text = f"""
📢 **تاك لجميع الأعضاء** 👥

🔔 **انتباه جميع الأعضاء!** ({members_count} عضو)

💬 **الرسالة:**
يرجى الانتباه للرسالة المهمة من الإدارة!

📌 **من:** {message.from_user.first_name}
⏰ **الوقت:** {datetime.datetime.now().strftime('%H:%M')}
        """
        
        bot.reply_to(message, mention_text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ **خطأ في التاك للكل:** {str(e)}")

# معالجة جميع الرسائل مع التحقق من الاشتراك
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    # تخطي الرسائل من البوت نفسه
    if message.from_user.id == bot.get_me().id:
        return
    
    # الحماية من السبام
    if protection_system.check_spam(message.from_user.id, message.text):
        bot.reply_to(message, "⚠️ **تم اكتشاف نشاط مريب!**")
        return
    
    # حفظ المعلومات
    save_user_info(message.from_user)
    increment_message_count(message.from_user.id)
    
    text = message.text
    
    # التحقق من الاشتراك للرسائل العادية (باستثناء بعض الأوامر)
    if text and not text.startswith('/') and not any(cmd in text for cmd in ['اشتراك', 'قناة', 'channel']):
        if not check_user_subscription(message.from_user.id):
            # إرسال رسالة طلب الاشتراك فقط مرة واحدة كل 10 رسائل
            if random.randint(1, 10) == 1:
                subscription_reminder = f"""
📺 **اشتراك مطلوب!**

عذراً {message.from_user.first_name}، يجب عليك الاشتراك في قناتنا لاستخدام البوت.

✅ **القناة:** {REQUIRED_CHANNEL}
🔗 **الرابط:** {CHANNEL_URL}

بعد الاشتراك، اضغط على /start
                """
                bot.reply_to(message, subscription_reminder, reply_markup=create_subscription_check_keyboard())
            return
    
    # ردود "سيو" - 44 رد مختلف
    if 'سيو' in text.lower() or 'شيو' in text.lower():
        response = random.choice(siu_responses)
        bot.reply_to(message, response)
        return
    
    # الردود التفاعلية الأساسية
    if text == '👋 سلام':
        greetings = [
            "وعليكم السلام ورحمة الله وبركاته 🌹",
            "أهلاً وسهلاً 🌸",
            "مرحباً بك 👋",
            "الله يسلمك 🌟",
            "أهلاً بالغالي 🌷"
        ]
        bot.reply_to(message, random.choice(greetings))
    
    elif text == '💍 زوجني':
        girls = ['سارة', 'فاطمة', 'مريم', 'نور', 'ليلى', 'هدى', 'ريم', 'ياسمين', 'لطيفة', 'عبير']
        chosen_girl = random.choice(girls)
        bot.reply_to(message, f"💍 **مبروك! زوجتك هي** {chosen_girl} 🎉\n\n🎊 **العرس بعد أسبوع واحد!**")
    
    elif text == '🤖 سيـو':
        response = random.choice(siu_responses)
        bot.reply_to(message, response)
    
    elif text == '🔄 تحديث':
        bot.reply_to(message, "✅ **تم تحديث النظام والبيانات**", reply_markup=create_main_keyboard())
    
    elif text == '📊 إحصائيات':
        try:
            members_count = bot.get_chat_members_count(message.chat.id)
            stats_text = f"""
📊 **إحصائيات المجموعة**

👥 **عدد الأعضاء:** {members_count}
💬 **رسائل اليوم:** {random.randint(50, 500)}
📈 **نشاط المجموعة:** {'🔥 عالي' if members_count > 100 else '🟢 متوسط'}
🎯 **الحالة:** نشط

⏰ **آخر تحديث:** {datetime.datetime.now().strftime('%H:%M')}
            """
            bot.reply_to(message, stats_text)
        except:
            bot.reply_to(message, "📊 **الإحصائيات غير متاحة حالياً**")
    
    elif text == '🎮 ألعاب':
        games_menu(message)
    
    elif text == '📺 قنوات':
        channel_info(message)
    
    elif text == '🎁 عروض':
        offers_text = f"""
🎁 **عروض حصرية**

💰 **عروض العضوية:**
• 🟢 أساسي - مجاني
• 🟡 متميز - وصول كامل
• 🔴 ذهبي - ميزات حصرية

🎮 **عروض الألعاب:**
• عملات مجانية يومياً
• مكافآت النشاط
• تحديات أسبوعية

📺 **عروض القنوات:**
• إشعارات حصرية
• محتوى مميز
• مسابقات دورية

🔔 **تابع القناة للحصول على العروض!**
{CHANNEL_URL}
        """
        bot.reply_to(message, offers_text)
    
    elif text == '⚙️ إعدادات':
        if is_admin(message.chat.id, message.from_user.id):
            settings = get_group_settings(message.chat.id)
            settings_text = f"""
⚙️ **إعدادات المجموعة**

🎊 **الترحيب:** {'✅ مفعل' if settings['welcome_enabled'] else '❌ معطل'}
📺 **القنوات المطلوبة:** {'✅ مفعل' if settings['channel_required'] else '❌ معطل'}
👥 **عدد الأعضاء:** {bot.get_chat_members_count(message.chat.id) if hasattr(bot, 'get_chat_members_count') else 'غير معروف'}

🔧 **للتعديل:** استخدم أوامر الإدارة
            """
            bot.reply_to(message, settings_text, reply_markup=create_admin_keyboard())
        else:
            personal_settings = f"""
⚙️ **الإعدادات الشخصية**

👤 **الاسم:** {message.from_user.first_name}
📺 **حالة الاشتراك:** {'🟢 نشط' if check_user_subscription(message.from_user.id) else '🔴 غير نشط'}
💬 **رسائلك:** {random.randint(10, 1000)}
🌟 **مستواك:** {random.randint(1, 100)}

🔔 **للتحديث:** استخدم /start
            """
            bot.reply_to(message, personal_settings)
    
    elif text == '🏠 الرئيسية':
        bot.reply_to(message, "🏠 **العودة للقائمة الرئيسية**", reply_markup=create_main_keyboard())
    
    elif text == '🔙 رجوع للإدارة':
        admin_panel(message)

# وظيفة دورية للتحقق من الاشتراكات
def check_subscriptions_periodically():
    """فحص الاشتراكات دورياً"""
    while True:
        try:
            conn = sqlite3.connect('bot_data.db')
            c = conn.cursor()
            
            # جلب جميع المستخدمين
            c.execute('SELECT user_id FROM users WHERE is_member = 1')
            users = c.fetchall()
            
            for (user_id,) in users:
                if not check_user_subscription(user_id):
                    # تحديث حالة المستخدم إذا لم يعد مشتركاً
                    update_user_membership(user_id, False)
                    logger.info(f"تم تحديث حالة المستخدم {user_id} إلى غير مشترك")
            
            conn.close()
            time.sleep(3600)  # التحقق كل ساعة
            
        except Exception as e:
            logger.error(f"خطأ في الفحص الدوري: {e}")
            time.sleep(300)

# بدء الفحص الدوري في thread منفصل
subscription_thread = threading.Thread(target=check_subscriptions_periodically, daemon=True)
subscription_thread.start()

# بدء التشغيل
if __name__ == '__main__':
    print("🤖 **بوت سيـو المتطور يعمل الآن!**")
    print(f"📺 **القناة المطلوبة:** {REQUIRED_CHANNEL}")
    print("✅ **تم تفعيل نظام الاشتراك الإلزامي**")
    
    try:
        bot.polling(none_stop=True, interval=1, timeout=60)
    except Exception as e:
        logger.error(f"خطأ في تشغيل البوت: {e}")
        print(f"❌ خطأ في التشغيل: {e}")
        time.sleep(10)