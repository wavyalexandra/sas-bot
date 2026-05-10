import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import os

# ─── НАСТРОЙКИ ────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ВАШ_ТОКЕН_ЗДЕСЬ")
MANAGER_CHAT_ID = os.environ.get("MANAGER_CHAT_ID", "ВАШ_CHAT_ID_ЗДЕСЬ")
CATALOG_FILE = "catalog.json"
CATALOG_PDF  = "catalog.pdf"
PHOTOS_DIR   = "photos"
TOPIC_ID     = 435  # ID темы в группе
# ──────────────────────────────────────────────────────────────

BED_ARTS = {"s1101","s1102","s1201","s1202","s1203","s1204","s1301","s1301c","s1401","s1402","s1403"}

bot = telebot.TeleBot(BOT_TOKEN)

with open(CATALOG_FILE, "r", encoding="utf-8") as f:
    CATALOG = json.load(f)

carts = {}
waiting_qty = {}
waiting_phone = {}
user_phones = {}

def get_cart(user_id):
    if user_id not in carts:
        carts[user_id] = {}
    return carts[user_id]

def find_item(art):
    for cat in CATALOG["categories"]:
        for item in cat["items"]:
            if item["art"] == art:
                return item
    return None

def get_photo_path(art):
    path = os.path.join(PHOTOS_DIR, f"{art}.jpg")
    return path if os.path.exists(path) else None

def cart_total(cart):
    total = 0
    for art, qty in cart.items():
        item = find_item(art)
        if item:
            total += item.get("price", 0) * qty
    return total

def format_cart(cart, phone=None):
    if not cart:
        return "Корзина пуста."
    lines = []
    for art, qty in cart.items():
        item = find_item(art)
        if not item:
            continue
        price = item.get("price", 0)
        subtotal = price * qty
        lines.append(f"• Арт. {art} — {item['name']}\n  {qty} шт. × {price} BYN = *{subtotal} BYN*")
    lines.append(f"\n💰 *Итого: {cart_total(cart)} BYN*")
    if phone:
        lines.append(f"📞 Телефон: {phone}")
    return "\n\n".join(lines)

def main_menu_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📦 Каталог товаров", callback_data="catalog"))
    kb.add(InlineKeyboardButton("🛒 Моя корзина", callback_data="cart"))
    return kb

def categories_kb():
    kb = InlineKeyboardMarkup()
    for i, cat in enumerate(CATALOG["categories"]):
        kb.add(InlineKeyboardButton(cat["name"], callback_data=f"cat_{i}"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="main"))
    return kb

def items_kb(cat_index, page=0, page_size=8):
    items = CATALOG["categories"][cat_index]["items"]
    kb = InlineKeyboardMarkup()
    start = page * page_size
    end = start + page_size
    for item in items[start:end]:
        label = f"Арт. {item['art']} — {item['name'][:25]} | {item.get('price',0)} BYN"
        kb.add(InlineKeyboardButton(label, callback_data=f"item_{item['art']}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Назад", callback_data=f"page_{cat_index}_{page-1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton("Далее ▶", callback_data=f"page_{cat_index}_{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("🛒 Корзина", callback_data="cart"))
    kb.add(InlineKeyboardButton("🔙 К категориям", callback_data="catalog"))
    return kb

def item_kb(art, cat_index):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Добавить в корзину", callback_data=f"add_{art}_{cat_index}"))
    kb.add(InlineKeyboardButton("🛒 Корзина", callback_data="cart"))
    kb.add(InlineKeyboardButton("🔙 К списку", callback_data=f"cat_{cat_index}"))
    return kb

def cart_kb(has_phone):
    kb = InlineKeyboardMarkup()
    if has_phone:
        kb.add(InlineKeyboardButton("✅ Отправить заявку менеджеру", callback_data="submit"))
    else:
        kb.add(InlineKeyboardButton("📞 Указать номер телефона", callback_data="ask_phone"))
    kb.add(InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear_cart"))
    kb.add(InlineKeyboardButton("🔙 В каталог", callback_data="catalog"))
    return kb

@bot.message_handler(commands=["start"])
def start(message):
    user = message.from_user.first_name
    chat_id = message.chat.id
    bot.send_message(
        chat_id,
        f"Привет, {user}! 👋\n\nДобро пожаловать в магазин *SAS Animal Accessory* 🐾\nСначала отправляю наш каталог, затем вы сможете выбрать товары и оформить заявку.",
        parse_mode="Markdown"
    )
    if os.path.exists(CATALOG_PDF):
        with open(CATALOG_PDF, "rb") as pdf:
            bot.send_document(chat_id, pdf, caption="📋 Каталог товаров SAS Animal Accessory 2026")
    bot.send_message(chat_id, "Выберите действие:", reply_markup=main_menu_kb())

@bot.callback_query_handler(func=lambda c: c.data == "main")
def go_main(call):
    bot.edit_message_text("Главное меню:", call.message.chat.id, call.message.message_id, reply_markup=main_menu_kb())

@bot.callback_query_handler(func=lambda c: c.data == "catalog")
def show_catalog(call):
    bot.edit_message_text("📦 *Каталог товаров*\n\nВыберите категорию:", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=categories_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def show_category(call):
    cat_index = int(call.data.split("_")[1])
    cat = CATALOG["categories"][cat_index]
    text = f"{cat['name']}\n\nВыберите товар:"
    kb = items_kb(cat_index, page=0)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("page_"))
def paginate(call):
    _, cat_index, page = call.data.split("_")
    cat_index, page = int(cat_index), int(page)
    cat = CATALOG["categories"][cat_index]
    text = f"{cat['name']}\n\nВыберите товар:"
    kb = items_kb(cat_index, page=page)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("item_"))
def show_item(call):
    art = call.data.split("_")[1]
    item = find_item(art)
    cat_index = 0
    for i, cat in enumerate(CATALOG["categories"]):
        if any(it["art"] == art for it in cat["items"]):
            cat_index = i
            break
    price = item.get("price", 0)
    text = f"📋 *{item['name']}*\nАртикул: `{item['art']}`\nРазмер: {item['size']}\nЦена: *{price} BYN*"
    if art in BED_ARTS:
        text += "\n\n🎨 *Доступны различные варианты тканей и расцветок — наш менеджер подберёт идеальный вариант специально для вас.*"
    photo_path = get_photo_path(art)
    if photo_path:
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        with open(photo_path, "rb") as photo:
            bot.send_photo(call.message.chat.id, photo, caption=text, parse_mode="Markdown", reply_markup=item_kb(art, cat_index))
    else:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=item_kb(art, cat_index))

@bot.callback_query_handler(func=lambda c: c.data.startswith("add_"))
def ask_quantity(call):
    art = call.data.split("_")[1]
    item = find_item(art)
    price = item.get("price", 0)
    waiting_qty[call.from_user.id] = art
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"Введите количество для *{item['name']}*\nЦена: {price} BYN за шт.",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.from_user.id in waiting_qty)
def receive_quantity(message):
    user_id = message.from_user.id
    art = waiting_qty.get(user_id)
    try:
        qty = int(message.text.strip())
        if qty <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "❗ Введите целое число больше 0.")
        return
    cart = get_cart(user_id)
    cart[art] = cart.get(art, 0) + qty
    del waiting_qty[user_id]
    item = find_item(art)
    price = item.get("price", 0)
    subtotal = price * cart[art]
    bot.send_message(
        message.chat.id,
        f"✅ *{item['name']}* — {cart[art]} шт.\n💰 Стоимость: *{subtotal} BYN*\n\nПродолжить выбор или перейти в корзину?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Продолжить выбор", callback_data="catalog")],
            [InlineKeyboardButton("🛒 Перейти в корзину", callback_data="cart")]
        ])
    )

@bot.callback_query_handler(func=lambda c: c.data == "ask_phone")
def ask_phone(call):
    waiting_phone[call.from_user.id] = True
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "📞 Введите ваш номер телефона для связи с менеджером:",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.from_user.id in waiting_phone)
def receive_phone(message):
    user_id = message.from_user.id
    phone = message.text.strip()
    user_phones[user_id] = phone
    del waiting_phone[user_id]
    cart = get_cart(user_id)
    text = "🛒 *Ваша корзина:*\n\n" + format_cart(cart, phone=phone)
    bot.send_message(
        message.chat.id,
        f"✅ Номер *{phone}* сохранён!\n\n" + text,
        parse_mode="Markdown",
        reply_markup=cart_kb(has_phone=True)
    )

@bot.callback_query_handler(func=lambda c: c.data == "cart")
def show_cart(call):
    user_id = call.from_user.id
    cart = get_cart(user_id)
    phone = user_phones.get(user_id)
    text = "🛒 *Ваша корзина:*\n\n" + format_cart(cart, phone=phone)
    kb = cart_kb(has_phone=bool(phone)) if cart else main_menu_kb()
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        # Если предыдущее сообщение было с фото — отправляем новое
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "clear_cart")
def clear_cart(call):
    carts[call.from_user.id] = {}
    bot.edit_message_text("🗑 Корзина очищена.", call.message.chat.id, call.message.message_id, reply_markup=main_menu_kb())

@bot.callback_query_handler(func=lambda c: c.data == "submit")
def submit_order(call):
    user = call.from_user
    cart = get_cart(user.id)
    if not cart:
        bot.answer_callback_query(call.id, "Корзина пуста!")
        return
    total = cart_total(cart)
    phone = user_phones.get(user.id, "не указан")
    lines = [f"📥 *Новая заявка*\n"]
    lines.append(f"👤 Клиент: [{user.first_name}](tg://user?id={user.id})")
    if user.username:
        lines.append(f"   @{user.username}")
    lines.append(f"   ID: `{user.id}`")
    lines.append(f"   📞 Телефон: {phone}\n")
    lines.append("📋 *Состав заказа:*")
    for art, qty in cart.items():
        item = find_item(art)
        name = item["name"] if item else "—"
        price = item.get("price", 0) if item else 0
        subtotal = price * qty
        lines.append(f"• Арт. `{art}` — {name}\n  {qty} шт. × {price} BYN = *{subtotal} BYN*")
    lines.append(f"\n💰 *Итого: {total} BYN*")
    try:
        bot.send_message(MANAGER_CHAT_ID, "\n".join(lines), parse_mode="Markdown", message_thread_id=TOPIC_ID)
        carts[user.id] = {}
        bot.edit_message_text(
            f"✅ *Заявка отправлена!*\n\n💰 Сумма вашего заказа: *{total} BYN*\n\nМенеджер свяжется с вами в ближайшее время. Спасибо! 🐾",
            call.message.chat.id, call.message.message_id,
            parse_mode="Markdown", reply_markup=main_menu_kb()
        )
    except Exception as e:
        bot.answer_callback_query(call.id, "Ошибка отправки. Попробуйте позже.")
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    print("✅ Бот запущен...")
    bot.infinity_polling()
