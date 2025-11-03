import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import json
import datetime
import sqlite3
import random
import requests
import os
import time
from threading import Thread

# تهيئة البوت
API_TOKEN = '8537993182:AAEqfQf57Lt_ToF85GbSLf9pMSTgT7NGWBE'
bot = telebot.TeleBot(API_TOKEN)

# قاعدة البيانات
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
                  warnings INTEGER DEFAULT 0)''')
    
    # جدول المحظورين
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users
                 (user_id INTEGER PRIMARY KEY,
                  banned_by INTEGER,
                  ban_date TEXT,
                  reason TEXT)''')
    
    # جدول المكتومين
    c.execute('''CREATE TABLE IF NOT EXISTS muted_users
                 (user_id INTEGER PRIMARY KEY,
                  muted_by INTEGER,
                  mute_date TEXT,
                  duration INTEGER)''')
    
    # جدول الإعدادات
    c.execute('''CREATE TABLE IF NOT EXISTS group_settings
                 (chat_id INTEGER PRIMARY KEY,
                  welcome_enabled INTEGER DEFAULT 1,
                  goodbye_enabled INTEGER DEFAULT 1,
                  max_warnings INTEGER DEFAULT 3)''')
    
    conn.commit()
    conn.close()

init_db()

# 44 رد مختلف لـ "سيو"
siu_responses = [
    "ليش فاضي اك مبك؟ 😄",
    "مو فاضي والله! 🏃‍♂️",
    "نعم، تفضل 🌟",
    "ما بك؟ كل شيء بخير 🎯",
    "فاضي شوي، شتريد؟ 🤔",
    "والله مو فاضي، عندي شغل 🚀",
    "اييه فاضي، حكيك 🎭",
    "شتبي؟ فاضي بس مادري شسويلك 💭",
    "فاضي وياك، تفضل 🌸",
    "لا مو فاضي، عندي مشاوير 🏃",
    "فاضي بس ماني مطلع برا 🏠",
    "اي فاضي، شقولك؟ 🎪",
    "فاضي مثل الهواء ☁️",
    "مو فاضي، دزلي خاص 🕵️",
    "فاضي لك وياك يا قلبي 💖",
    "لا والله مشغول 📚",
    "فاضي وانت عمري 🎁",
    "شتبي؟ ماني فاضي للعب 🎮",
    "فاضي بس للجادين فقط ⚡",
    "مو فاضي، عندي دورة حياة 🐛",
    "فاضي مثل بحر 🌊",
    "لا فاضي، عندي أهداف 🎯",
    "فاضي لك ويا حبايبي 🌹",
    "شتبي؟ فاضي بس للكلام الهادف 💬",
    "فاضي وانت نجمي 🌟",
    "مو فاضي، دبرلي حالك 🤷‍♂️",
    "فاضي بس للطيبين 😇",
    "لا فاضي، عندي مشاريع 🏗️",
    "فاضي وياك يا غالي 💎",
    "شتبي؟ فاضي بس للمهمات 🎖️",
    "فاضي مثل سحابة 🌤️",
    "مو فاضي، عندي خطط 🗓️",
    "فاضي لك ويا روحي 🫀",
    "لا فاضي، عندي أحلام 🌙",
    "فاضي وياك يا حبيبي ❤️",
    "شتبي؟ فاضي بس للعمل 💼",
    "فاضي مثل نهر 🏞️",
    "مو فاضي، عندي طموحات 🚀",
    "فاضي لك ويا قمر 🌕",
    "لا فاضي، عندي أمنيات 🌠",
    "فاضي وياك يا حياتي 🌸",
    "شتبي؟ فاضي بس للتحديات ⚔️",
    "فاضي مثل نجمة 🌟",
    "آه فاضي، شتريد مني؟ 🎯"
]

# لوحة المفاتيح الرئيسية
def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = [
        'زوجني', 'سلام', 'سيو',
        '🔄 تحديث', '📊 إحصائيات', '🎲 العاب',
        '🕋 قرآن', '📿 دعاء', '🌤 طقس',
        '💰 محول العملات', '📅 تاريخ', '⏰ وقت',
        '🎯 كرة القدم', '📢 إذاعة', '⚙️ إعدادات',
        '👥 الأعضاء', '📈 ترند', '🔍 بحث',
        '🎵 موسيقى', '📸 صورة', '🎬 فيديو',
        '📝 ملاحظة', '🔔 منبه', '🧮 آلة حاسبة',
        '📚 مكتبة', '🎨 رسم', '🔐 خصوصية',
        '🌐 ويب', '📡 خادم', '📂 ملفات',
        '🛡 حماية', '🎭 تسلية', '📣 إعلان'
    ]
    for i in range(0, len(buttons), 3):
        keyboard.add(*buttons[i:i+3])
    return keyboard

# لوحة المفاتيح الإدارية
def create_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        '🔨 حظر', '🔇 كتم', '🔊 إلغاء كتم',
        '⚠️ تحذير', '📊 إحصائيات المجموعة',
        '⚙️ إعدادات المجموعة', '🧹 تنظيف',
        '📢 إعلان للكل', '👥 صلاحيات',
        '📝 تغيير الوصف', '🏷 تغيير الاسم'
    ]
    for i in range(0, len(buttons), 2):
        keyboard.add(*buttons[i:i+2])
    keyboard.add('🏠 الرئيسية')
    return keyboard

# حفظ معلومات المستخدم
def save_user_info(user):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute('''INSERT OR IGNORE INTO users 
                 (user_id, username, first_name, last_name, join_date)
                 VALUES (?, ?, ?, ?, ?)''',
              (user.id, user.username, user.first_name, 
               user.last_name, datetime.datetime.now().isoformat()))
    
    c.execute('''UPDATE users SET username=?, first_name=?, last_name=?
                 WHERE user_id=?''',
              (user.username, user.first_name, user.last_name, user.id))
    
    conn.commit()
    conn.close()

# الأوامر الأساسية
@bot.message_handler(commands=['start'])
def send_welcome(message):
    save_user_info(message.from_user)
    
    welcome_text = """
    🎊 أهلاً وسهلاً بك في البوت المتطور!
    
    📋 الأوامر المتاحة (33 أمر):
    
    🛡 إدارة المجموعة:
    /ban - حظر عضو
    /unban - فك حظر
    /mute - كتم عضو  
    /unmute - فك كتم
    /warn - تحذير عضو
    /unwarn - إزالة تحذير
    /kick - طرد عضو
    /promote - ترقية مشرف
    /demote - إزالة مشرف
    
    📊 معلومات:
    /info - معلومات العضو
    /group - معلومات المجموعة
    /stats - إحصائيات
    /members - قائمة الأعضاء
    /admins - قائمة المشرفين
    
    🎮 تسلية:
    /game - ألعاب
    /joke - نكتة
    /quote - اقتباس
    /love - حساب الحب
    /zodiac - برجك
    
    📡 خدمات:
    /weather - الطقس
    /time - الوقت
    /date - التاريخ
    /calc - آلة حاسبة
    /currency - محول عملات
    
    🎵 وسائط:
    /music - تحميل موسيقى
    /video - تحميل فيديو
    /image - البحث عن صور
    
    ⚙️ أخرى:
    /settings - الإعدادات
    /broadcast - إذاعة
    /clean - تنظيف الدردشة
    /backup - نسخ احتياطي
    /restart - إعادة تشغيل
    
    💬 مميزات خاصة:
    • 44 رد مختلف لـ "سيو"
    • ردود تلقائية على "سلام" و "زوجني"
    
    🎯 استخدم الأزرار للوصول السريع!
    """
    
    bot.reply_to(message, welcome_text, reply_markup=create_main_keyboard())

# 1. معلومات العضو
@bot.message_handler(commands=['info'])
def user_info(message):
    save_user_info(message.from_user)
    
    if message.reply_to_message:
        user = message.reply_to_message.from_user
    else:
        user = message.from_user
    
    user_data = get_user_info(user.id)
    
    if user_data:
        info_text = f"""
        📊 معلومات العضو:
        
        🆔 الآيدي: {user_data[0]}
        👤 الاسم: {user_data[2]} {user_data[3] or ''}
        📛 اليوزر: @{user_data[1] or 'لا يوجد'}
        ⚠️ التحذيرات: {user_data[5]}
        📅 تاريخ الانضمام: {user_data[4][:10]}
        """
    else:
        info_text = "❌ لم يتم العثور على معلومات المستخدم"
    
    bot.reply_to(message, info_text)

# 2. حظر العضو
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ يرجى الرد على الرسالة التي تريد حظر مرسلها")
        return
    
    user_to_ban = message.reply_to_message.from_user
    reason = ' '.join(message.text.split()[1:]) or 'لا يوجد سبب'
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO banned_users VALUES (?, ?, ?, ?)',
              (user_to_ban.id, message.from_user.id, datetime.datetime.now().isoformat(), reason))
    conn.commit()
    conn.close()
    
    try:
        bot.ban_chat_member(message.chat.id, user_to_ban.id)
        bot.reply_to(message, f"✅ تم حظر المستخدم {user_to_ban.first_name}\nالسبب: {reason}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في الحظر: {e}")

# 3. فك الحظر
@bot.message_handler(commands=['unban'])
def unban_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ يرجى الرد على رسالة العضو المحظور")
        return
    
    user_to_unban = message.reply_to_message.from_user
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM banned_users WHERE user_id = ?', (user_to_unban.id,))
    conn.commit()
    conn.close()
    
    try:
        bot.unban_chat_member(message.chat.id, user_to_unban.id)
        bot.reply_to(message, f"✅ تم فك حظر المستخدم {user_to_unban.first_name}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في فك الحظر: {e}")

# 4. كتم العضو
@bot.message_handler(commands=['mute'])
def mute_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ يرجى الرد على الرسالة التي تريد كتم مرسلها")
        return
    
    user_to_mute = message.reply_to_message.from_user
    duration = 60  # دقيقة واحدة افتراضياً
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO muted_users VALUES (?, ?, ?, ?)',
              (user_to_mute.id, message.from_user.id, datetime.datetime.now().isoformat(), duration))
    conn.commit()
    conn.close()
    
    try:
        bot.restrict_chat_member(message.chat.id, user_to_mute.id, 
                               until_date=time.time() + duration * 60,
                               can_send_messages=False)
        bot.reply_to(message, f"🔇 تم كتم المستخدم {user_to_mute.first_name} لمدة {duration} دقيقة")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في الكتم: {e}")

# 5. فك الكتم
@bot.message_handler(commands=['unmute'])
def unmute_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ يرجى الرد على الرسالة التي تريد إلغاء كتم مرسلها")
        return
    
    user_to_unmute = message.reply_to_message.from_user
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM muted_users WHERE user_id = ?', (user_to_unmute.id,))
    conn.commit()
    conn.close()
    
    try:
        bot.restrict_chat_member(message.chat.id, user_to_unmute.id,
                               can_send_messages=True,
                               can_send_media_messages=True,
                               can_send_other_messages=True)
        bot.reply_to(message, f"🔊 تم إلغاء كتم المستخدم {user_to_unmute.first_name}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في إلغاء الكتم: {e}")

# 6. تحذير العضو
@bot.message_handler(commands=['warn'])
def warn_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ يرجى الرد على الرسالة التي تريد تحذير مرسلها")
        return
    
    user_to_warn = message.reply_to_message.from_user
    reason = ' '.join(message.text.split()[1:]) or 'لا يوجد سبب'
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('UPDATE users SET warnings = warnings + 1 WHERE user_id = ?', (user_to_warn.id,))
    c.execute('SELECT warnings FROM users WHERE user_id = ?', (user_to_warn.id,))
    warnings = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"⚠️ تم تحذير {user_to_warn.first_name}\nالتحذيرات: {warnings}/3\nالسبب: {reason}")
    
    if warnings >= 3:
        try:
            bot.ban_chat_member(message.chat.id, user_to_warn.id)
            bot.reply_to(message, f"🚫 تم حظر {user_to_warn.first_name} بسبب تجاوز الحد الأقصى للتحذيرات")
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ في الحظر التلقائي: {e}")

# 7. إزالة التحذير
@bot.message_handler(commands=['unwarn'])
def unwarn_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ يرجى الرد على الرسالة التي تريد إزالة تحذير مرسلها")
        return
    
    user_to_unwarn = message.reply_to_message.from_user
    
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('UPDATE users SET warnings = GREATEST(warnings - 1, 0) WHERE user_id = ?', (user_to_unwarn.id,))
    c.execute('SELECT warnings FROM users WHERE user_id = ?', (user_to_unwarn.id,))
    warnings = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ تم إزالة تحذير من {user_to_unwarn.first_name}\nالتحذيرات المتبقية: {warnings}")

# 8. طرد العضو
@bot.message_handler(commands=['kick'])
def kick_user(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ يرجى الرد على الرسالة التي تريد طرد مرسلها")
        return
    
    user_to_kick = message.reply_to_message.from_user
    
    try:
        bot.ban_chat_member(message.chat.id, user_to_kick.id)
        bot.unban_chat_member(message.chat.id, user_to_kick.id)
        bot.reply_to(message, f"👢 تم طرد المستخدم {user_to_kick.first_name}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في الطرد: {e}")

# 9. ترقية مشرف
@bot.message_handler(commands=['promote'])
def promote_user(message):
    if not is_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمالك فقط!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ يرجى الرد على الرسالة التي تريد ترقية مرسلها")
        return
    
    user_to_promote = message.reply_to_message.from_user
    
    try:
        bot.promote_chat_member(message.chat.id, user_to_promote.id,
                              can_change_info=True,
                              can_delete_messages=True,
                              can_invite_users=True,
                              can_restrict_members=True,
                              can_pin_messages=True,
                              can_promote_members=False)
        bot.reply_to(message, f"⬆️ تم ترقية {user_to_promote.first_name} إلى مشرف")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في الترقية: {e}")

# 10. إزالة مشرف
@bot.message_handler(commands=['demote'])
def demote_user(message):
    if not is_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمالك فقط!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ يرجى الرد على الرسالة التي تريد إزالة صلاحيات مرسلها")
        return
    
    user_to_demote = message.reply_to_message.from_user
    
    try:
        bot.promote_chat_member(message.chat.id, user_to_demote.id,
                              can_change_info=False,
                              can_delete_messages=False,
                              can_invite_users=False,
                              can_restrict_members=False,
                              can_pin_messages=False,
                              can_promote_members=False)
        bot.reply_to(message, f"⬇️ تم إزالة صلاحيات المشرف من {user_to_demote.first_name}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في إزالة الصلاحيات: {e}")

# 11. معلومات المجموعة
@bot.message_handler(commands=['group'])
def group_info(message):
    chat = bot.get_chat(message.chat.id)
    
    info_text = f"""
    📊 معلومات المجموعة:
    
    🏷️ الاسم: {chat.title}
    📝 الوصف: {chat.description or 'لا يوجد'}
    👥 عدد الأعضاء: {bot.get_chat_members_count(message.chat.id)}
    🆔 الآيدي: {chat.id}
    📌 الرابط: {chat.invite_link or 'غير متاح'}
    🔒 النوع: {'خاص' if chat.type == 'private' else 'عام'}
    """
    
    bot.reply_to(message, info_text)

# 12. الإحصائيات
@bot.message_handler(commands=['stats'])
def stats(message):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM banned_users')
    total_banned = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM muted_users')
    total_muted = c.fetchone()[0]
    
    conn.close()
    
    stats_text = f"""
    📈 إحصائيات البوت:
    
    👥 إجمالي المستخدمين: {total_users}
    🚫 المحظورين: {total_banned}
    🔇 المكتومين: {total_muted}
    💻 وقت التشغيل: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    bot.reply_to(message, stats_text)

# 13. قائمة الأعضاء
@bot.message_handler(commands=['members'])
def members_list(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    try:
        members_count = bot.get_chat_members_count(message.chat.id)
        bot.reply_to(message, f"👥 عدد أعضاء المجموعة: {members_count}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في جلب المعلومات: {e}")

# 14. قائمة المشرفين
@bot.message_handler(commands=['admins'])
def admins_list(message):
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        admins_text = "👑 قائمة المشرفين:\n\n"
        
        for admin in admins:
            status = "🛡 مالك" if admin.status == 'creator' else "⭐ مشرف"
            admins_text += f"{status}: {admin.user.first_name} (@{admin.user.username or 'لا يوجد'})\n"
        
        bot.reply_to(message, admins_text)
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في جلب المشرفين: {e}")

# 15. الألعاب
@bot.message_handler(commands=['game'])
def games_menu(message):
    games_text = """
    🎮 قائمة الألعاب:
    
    🎲 /dice - رمي النرد
    🎯 /dart - رمي السهم
    🏀 /basketball - كرة السلة
    ⚽ /football - كرة القدم
    🎰 /slot - ماكينة القمار
    ❓ /quiz - مسابقة
    🔢 /math - مسائل رياضية
    """
    
    bot.reply_to(message, games_text)

# 16. النكات
@bot.message_handler(commands=['joke'])
def send_joke(message):
    jokes = [
        "لماذا لا يثق العلماء في الذرات؟ لأنها تصنع كل شيء!",
        "ماذا قال الجدار للجدار الآخر؟ سأراك في الزاوية!",
        "لماذا يحب الكمبيوتر الطقس البارد؟ لأنه يملك نوافذ!",
        "ماذا قال البحر للشاطئ؟ لا شيء.. فقط موجه!",
    ]
    
    bot.reply_to(message, random.choice(jokes))

# 17. الاقتباسات
@bot.message_handler(commands=['quote'])
def send_quote(message):
    quotes = [
        "“النجاح ليس نهائياً، والفشل ليس قاتلاً: الشجاعة هي التي تهم.” - وينستون تشرشل",
        "“الحياة إما مغامرة جريئة أو لا شيء.” - هيلين كيلر",
        "“الطريقة الوحيدة للقيام بعمل رائع هي أن تحب ما تفعله.” - ستيف جوبز",
        "“لا تحلم بالنجاح، اعمل من أجله.” - مجهول",
    ]
    
    bot.reply_to(message, random.choice(quotes))

# 18. حساب الحب
@bot.message_handler(commands=['love'])
def love_calculator(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ يرجى الرد على الشخص الذي تريد حساب نسبة الحب معه")
        return
    
    user1 = message.from_user.first_name
    user2 = message.reply_to_message.from_user.first_name
    
    love_percentage = random.randint(10, 100)
    
    love_text = f"""
    💖 حاسبة الحب:
    
    👤 {user1}
    💕 {love_percentage}%
    👤 {user2}
    
    {"💘 حب حقيقي!" if love_percentage > 80 else "❤️ جيد!" if love_percentage > 50 else "💔 تحتاج للمزيد من الجهد"}
    """
    
    bot.reply_to(message, love_text)

# 19. الأبراج
@bot.message_handler(commands=['zodiac'])
def zodiac_sign(message):
    signs = {
        'الحمل': 'اليوم سيكون يومًا مثيرًا لك!',
        'الثور': 'حان الوقت لاتخاذ قرارات مهمة.',
        'الجوزاء': 'ستحصل على أخبار سارة قريبًا.',
        'السرطان': 'ركز على علاقاتك الشخصية.',
        'الأسد': 'يوم مناسب للإبداع والعمل.',
        'العذراء': 'انتبه لصحتك اليوم.',
        'الميزان': 'توازن في جميع جوانب حياتك.',
        'العقرب': 'تحتاج للاسترخاء قليلاً.',
        'القوس': 'مغامرة جديدة تنتظرك.',
        'الجدي': 'عمل شاق سيعطي نتائج.',
        'الدلو': 'افكار مبتكرة ستظهر.',
        'الحوت': 'يوم عاطفي وحالم.'
    }
    
    sign = random.choice(list(signs.keys()))
    prediction = signs[sign]
    
    zodiac_text = f"""
    🌟 برجك اليوم:
    
    📛 البرج: {sign}
    🔮 توقعات اليوم: {prediction}
    ✨ الحظ: {random.randint(1, 5)*'⭐'}
    """
    
    bot.reply_to(message, zodiac_text)

# 20. الطقس
@bot.message_handler(commands=['weather'])
def weather(message):
    cities = ['الرياض', 'جدة', 'دبي', 'القاهرة', 'الدار البيضاء']
    city = random.choice(cities)
    temperature = random.randint(15, 45)
    conditions = ['☀️ مشمس', '⛅ غائم جزئياً', '🌧️ ممطر', '🌫️ ضباب']
    condition = random.choice(conditions)
    
    weather_text = f"""
    🌤 حالة الطقس:
    
    🏙️ المدينة: {city}
    🌡️ درجة الحرارة: {temperature}°C
    📊 الحالة: {condition}
    💨 الرطوبة: {random.randint(30, 80)}%
    """
    
    bot.reply_to(message, weather_text)

# 21. الوقت
@bot.message_handler(commands=['time'])
def current_time(message):
    from datetime import datetime
    now = datetime.now()
    
    time_text = f"""
    ⏰ الوقت الحالي:
    
    🕒 الوقت: {now.strftime("%H:%M:%S")}
    📅 التاريخ: {now.strftime("%Y-%m-%d")}
    🌍 المنطقة الزمنية: UTC+3
    """
    
    bot.reply_to(message, time_text)

# 22. التاريخ
@bot.message_handler(commands=['date'])
def current_date(message):
    import hijri_converter
    from datetime import datetime
    
    today = datetime.now()
    
    try:
        hijri = hijri_converter.Hijri.today()
        hijri_date = f"{hijri.day} {hijri.month_name()} {hijri.year} هـ"
    except:
        hijri_date = "غير متاح"
    
    date_text = f"""
    📅 التاريخ:
    
    📆 الميلادي: {today.strftime("%Y-%m-%d")}
    🌙 الهجري: {hijri_date}
    🗓️ اليوم: {today.strftime("%A")}
    """
    
    bot.reply_to(message, date_text)

# 23. الآلة الحاسبة
@bot.message_handler(commands=['calc'])
def calculator(message):
    try:
        expression = ' '.join(message.text.split()[1:])
        if not expression:
            bot.reply_to(message, "❌ يرجى إدخال عملية حسابية\nمثال: /calc 2+2")
            return
        
        # الأمان: التحقق من أن العملية تحتوي على رموز حسابية فقط
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in expression):
            bot.reply_to(message, "❌ تحتوي العملية على رموز غير مسموحة")
            return
        
        result = eval(expression)
        bot.reply_to(message, f"🧮 النتيجة: {expression} = {result}")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في العملية الحسابية: {e}")

# 24. محول العملات
@bot.message_handler(commands=['currency'])
def currency_converter(message):
    parts = message.text.split()
    if len(parts) != 4:
        bot.reply_to(message, "❌ استخدم: /currency [المبلغ] [من] [إلى]\nمثال: /currency 100 USD SAR")
        return
    
    try:
        amount = float(parts[1])
        from_curr = parts[2].upper()
        to_curr = parts[3].upper()
        
        # أسعار افتراضية (في التطبيق الحقيقي استخدم API)
        rates = {
            'USD': {'SAR': 3.75, 'EUR': 0.85, 'EGP': 30.9},
            'SAR': {'USD': 0.27, 'EUR': 0.23, 'EGP': 8.24},
            'EUR': {'USD': 1.18, 'SAR': 4.42, 'EGP': 36.35}
        }
        
        if from_curr in rates and to_curr in rates[from_curr]:
            converted = amount * rates[from_curr][to_curr]
            bot.reply_to(message, f"💰 {amount} {from_curr} = {converted:.2f} {to_curr}")
        else:
            bot.reply_to(message, "❌ العملة غير مدعومة")
    except ValueError:
        bot.reply_to(message, "❌ المبلغ يجب أن يكون رقم")

# 25. تحميل الموسيقى
@bot.message_handler(commands=['music'])
def music_download(message):
    bot.reply_to(message, "🎵 خدمة تحميل الموسيقى قيد التطوير...")

# 26. تحميل الفيديو
@bot.message_handler(commands=['video'])
def video_download(message):
    bot.reply_to(message, "🎬 خدمة تحميل الفيديو قيد التطوير...")

# 27. البحث عن الصور
@bot.message_handler(commands=['image'])
def image_search(message):
    query = ' '.join(message.text.split()[1:])
    if not query:
        bot.reply_to(message, "❌ يرجى إدخال كلمة للبحث\nمثال: /image مناظر طبيعية")
        return
    
    bot.reply_to(message, f"📸 البحث عن: {query}\nالخدمة قيد التطوير...")

# 28. الإعدادات
@bot.message_handler(commands=['settings'])
def settings_menu(message):
    settings_text = """
    ⚙️ إعدادات البوت:
    
    🔔 الإشعارات: ✅ مفعل
    🌐 اللغة: العربية
    🎨 السمة: فاتحة
    🔒 الخصوصية: عالية
    📊 الإحصائيات: ✅ مفعل
    
    Use buttons below to change settings.
    """
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🔔 الإشعارات", callback_data="notifications"),
        InlineKeyboardButton("🌐 اللغة", callback_data="language")
    )
    keyboard.add(
        InlineKeyboardButton("🎨 السمة", callback_data="theme"),
        InlineKeyboardButton("🔒 الخصوصية", callback_data="privacy")
    )
    
    bot.reply_to(message, settings_text, reply_markup=keyboard)

# 29. الإذاعة
@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    broadcast_text = ' '.join(message.text.split()[1:])
    if not broadcast_text:
        bot.reply_to(message, "❌ يرجى إدخال نص للإذاعة\nمثال: /broadcast مرحبا بالجميع")
        return
    
    # في التطبيق الحقيقي، أرسل للجميع
    bot.reply_to(message, f"📢 إذاعة: {broadcast_text}")

# 30. تنظيف الدردشة
@bot.message_handler(commands=['clean'])
def clean_chat(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    try:
        # هذا مثال بسيط، في التطبيق الحقيقي تحتاج لحذف الرسائل
        bot.reply_to(message, "🧹 تم تنظيف الدردشة (وهمي)")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في التنظيف: {e}")

# 31. النسخ الاحتياطي
@bot.message_handler(commands=['backup'])
def backup_data(message):
    if not is_admin(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمشرفين فقط!")
        return
    
    try:
        # إنشاء نسخة احتياطية
        import shutil
        shutil.copy2('bot_data.db', f'backup_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        bot.reply_to(message, "✅ تم إنشاء نسخة احتياطية من البيانات")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ في النسخ الاحتياطي: {e}")

# 32. إعادة التشغيل
@bot.message_handler(commands=['restart'])
def restart_bot(message):
    if not is_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ هذا الأمر للمالك فقط!")
        return
    
    bot.reply_to(message, "🔄 إعادة تشغيل البوت...")
    # في التطبيق الحقيقي، أضف منطق إعادة التشغيل هنا
    os._exit(1)

# 33. المساعدة
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
    ℹ️ قائمة الأوامر الكاملة (33 أمر):
    
    🛡 الإدارة: ban, unban, mute, unmute, warn, unwarn, kick, promote, demote
    📊 المعلومات: info, group, stats, members, admins  
    🎮 التسلية: game, joke, quote, love, zodiac
    📡 الخدمات: weather, time, date, calc, currency
    🎵 الوسائط: music, video, image
    ⚙️ أخرى: settings, broadcast, clean, backup, restart
    
    💬 مميزات خاصة:
    • 44 رد مختلف لـ "سيو"
    • ردود تلقائية على "سلام" و "زوجني"
    
    💡 استخدم /command للمساعدة حول أمر محدد
    """
    
    bot.reply_to(message, help_text)

# الدوال المساعدة
def get_user_info(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def is_admin(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

def is_creator(chat_id, user_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status == 'creator'
    except:
        return False

# الردود على النصوص
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    save_user_info(message.from_user)
    text = message.text.lower()
    
    # ردود "سيو" - 44 رد مختلف
    if 'سيو' in text:
        response = random.choice(siu_responses)
        bot.reply_to(message, response)
    
    # ردود أخرى
    elif text == 'زوجني':
        girls = ['سارة', 'فاطمة', 'مريم', 'نور', 'ليلى', 'هدى', 'ريم', 'ياسمين']
        chosen_girl = random.choice(girls)
        bot.reply_to(message, f"💍 مبروك! زوجتك هي {chosen_girl} 🎉")
    
    elif text == 'سلام':
        user_info = get_user_info(message.from_user.id)
        if user_info:
            name = user_info[2] or 'العضو'
            bot.reply_to(message, f"وعليكم السلام ورحمة الله وبركاته 🌹\nكيف حالك يا {name}؟")
    
    elif text == '🔄 تحديث':
        bot.reply_to(message, "✅ تم تحديث البيانات", reply_markup=create_main_keyboard())
    
    elif text == '📊 إحصائيات':
        stats(message)
    
    elif text == '🎲 العاب':
        games_menu(message)
    
    elif text == '🕋 قرآن':
        bot.reply_to(message, "📖 خدمة القرآن قيد التطوير...")
    
    elif text == '📿 دعاء':
        bot.reply_to(message, "🤲 خدمة الأدعية قيد التطوير...")
    
    elif text == '🌤 طقس':
        weather(message)
    
    elif text == '💰 محول العملات':
        bot.reply_to(message, "💱 استخدم: /currency [المبلغ] [من] [إلى]")
    
    elif text == '📅 تاريخ':
        current_date(message)
    
    elif text == '⏰ وقت':
        current_time(message)
    
    elif text == '🎯 كرة القدم':
        bot.reply_to(message, "⚽ خدمة كرة القدم قيد التطوير...")
    
    elif text == '📢 إذاعة':
        bot.reply_to(message, "📢 استخدم: /broadcast [النص]")
    
    elif text == '⚙️ إعدادات':
        settings_menu(message)
    
    elif text == '👥 الأعضاء':
        members_list(message)
    
    elif text == '📈 ترند':
        bot.reply_to(message, "📊 خدمة الترند قيد التطوير...")
    
    elif text == '🔍 بحث':
        bot.reply_to(message, "🔎 خدمة البحث قيد التطوير...")
    
    elif text == '🎵 موسيقى':
        music_download(message)
    
    elif text == '📸 صورة':
        bot.reply_to(message, "📷 استخدم: /image [كلمة البحث]")
    
    elif text == '🎬 فيديو':
        video_download(message)
    
    elif text == '📝 ملاحظة':
        bot.reply_to(message, "📋 خدمة الملاحظات قيد التطوير...")
    
    elif text == '🔔 منبه':
        bot.reply_to(message, "⏰ خدمة المنبه قيد التطوير...")
    
    elif text == '🧮 آلة حاسبة':
        bot.reply_to(message, "🧮 استخدم: /calc [عملية حسابية]")
    
    elif text == '📚 مكتبة':
        bot.reply_to(message, "📚 خدمة المكتبة قيد التطوير...")
    
    elif text == '🎨 رسم':
        bot.reply_to(message, "🖼 خدمة الرسم قيد التطوير...")
    
    elif text == '🔐 خصوصية':
        bot.reply_to(message, "🔒 إعدادات الخصوصية قيد التطوير...")
    
    elif text == '🌐 ويب':
        bot.reply_to(message, "🌐 خدمات الويب قيد التطوير...")
    
    elif text == '📡 خادم':
        bot.reply_to(message, "🖥 معلومات الخادم قيد التطوير...")
    
    elif text == '📂 ملفات':
        bot.reply_to(message, "📁 خدمة الملفات قيد التطوير...")
    
    elif text == '🛡 حماية':
        bot.reply_to(message, "🛡️ إعدادات الحماية قيد التطوير...")
    
    elif text == '🎭 تسلية':
        games_menu(message)
    
    elif text == '📣 إعلان':
        broadcast_message(message)
    
    elif text == '🏠 الرئيسية':
        bot.reply_to(message, "🏠 العودة للقائمة الرئيسية", reply_markup=create_main_keyboard())
    
    # التحقق من المكتومين
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM muted_users WHERE user_id = ?', (message.from_user.id,))
    if c.fetchone():
        bot.delete_message(message.chat.id, message.message_id)
    conn.close()

# معالجة الردود
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "notifications":
        bot.answer_callback_query(call.id, "🔔 إعدادات الإشعارات")
    elif call.data == "language":
        bot.answer_callback_query(call.id, "🌐 تغيير اللغة")
    elif call.data == "theme":
        bot.answer_callback_query(call.id, "🎨 تغيير السمة")
    elif call.data == "privacy":
        bot.answer_callback_query(call.id, "🔒 إعدادات الخصوصية")

# تشغيل البوت
if __name__ == '__main__':
    print("🤖 البوت يعمل الآن مع 44 رد مختلف لـ 'سيو'!")
    print("💬 جرب ارسال 'سيو' لاكتشاف الردود المختلفة")
    bot.polling(none_stop=True)