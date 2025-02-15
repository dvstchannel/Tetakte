
import html
from telegram import Message, Update, Bot, User, Chat, ParseMode
from typing import List, Optional
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html
from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GKICK_ERRORS = {
    "Người dùng là quản trị viên của cuộc trò chuyện",
    "Không tìm thấy trò chuyện",
    "Không đủ quyền hạn chế / không hạn chế thành viên trò chuyện",
    "User_not_participant",
    "Peer_id_invalid",
    "Trò chuyện nhóm đã bị vô hiệu hóa",
    "Cần phải là người mời người dùng để loại bỏ nó khỏi một nhóm cơ bản",
    "Chat_admin_required",
    "Chỉ người tạo ra một nhóm cơ bản mới có thể yêu cầu quản trị viên nhóm",
    "Channel_private",
    "Không có trong cuộc trò chuyện",
    "Phương pháp chỉ khả dụng cho các cuộc trò chuyện nhóm và kênh siêu nhỏ",
    "Không tìm thấy tin nhắn trả lời"
}

@run_async
def gkick(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message
    user_id = extract_user(message, args)
    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message in GKICK_ERRORS:
            pass
        else:
            message.reply_text("Người dùng không thể bị kick trên toàn cầu vì: {}".format(excp.message))
            return
    except TelegramError:
            pass

    if not user_id:
        message.reply_text("Bạn dường như không đề cập đến một người dùng")
        return
    if int(user_id) in SUDO_USERS or int(user_id) in SUPPORT_USERS:
        message.reply_text("OHHH! Ai đó đang cố gắng thu hút người dùng sudo/hỗ trợ! *Lấy bỏng ngô*")
        return
    if int(user_id) == OWNER_ID:
        message.reply_text("Chà! Một người nào đó thật là noob đến nỗi anh ta muốn gạ gẫm chủ sở hữu của tôi! *Lấy Khoai tây chiên*")
        return
    if int(user_id) == bot.id:
        message.reply_text("OHH... Hãy để tôi đá chính mình.. Không đời nào... ")
        return
    chats = get_all_chats()
    message.reply_text("Đang kick @{} khỏi toàn bộ nhóm".format(user_chat.username))
    for chat in chats:
        try:
             bot.unban_chat_member(chat.chat_id, user_id)  # Unban_member = kick (and not ban)
        except BadRequest as excp:
            if excp.message in GKICK_ERRORS:
                pass
            else:
                message.reply_text("Người dùng không thể bị kick trên toàn cầu vì: {}".format(excp.message))
                return
        except TelegramError:
            pass

GKICK_HANDLER = CommandHandler("duoicho", gkick, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
dispatcher.add_handler(GKICK_HANDLER)                              
