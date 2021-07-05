import html
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.global_bans_sql as sql
from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GBAN
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "Người dùng là quản trị viên của cuộc trò chuyện",
    "Trò chuyện không tìm thấy",
    "Không đủ quyền hạn chế / không hạn chế thành viên trò chuyện",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Chỉ người tạo một nhóm cơ bản mới có thể yêu cầu quản trị viên nhóm",
    "Channel_private",
    "Không có trong cuộc trò chuyện",
    "Không thể xóa chủ sở hữu cuộc trò chuyện",
}

UNGBAN_ERRORS = {
    "Người dùng là quản trị viên của cuộc trò chuyện",
    "Chat not found",
    "Không đủ quyền hạn chế / không hạn chế thành viên trò chuyện",
    "User_not_participant",
    "Phương pháp chỉ khả dụng cho các cuộc trò chuyện nhóm và kênh",
    "Not in the chat",
    "Channel_private",
    "Chat_admin_required",
    "Peer_id_invalid",
    "User not found",
}


@run_async
def gban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Có vẻ như bạn không đề cập đến người dùng hoặc ID được chỉ định không chính xác ..")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Tôi theo dõi, bằng con mắt nhỏ của mình ... một cuộc chiến tranh dành cho người dùng sudo! Tại sao các bạn lại bật nhau!")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("OOOH ai đó đang cố gắng thu hút người dùng hỗ trợ! * lấy bỏng ngô *")
        return

    if user_id == bot.id:
        message.reply_text("-_- Thật buồn cười, tôi tô màu rồi nên không bay màu được? Rất vui..")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("Đó không phải là một người dùng!")
        return

    if sql.is_user_gbanned(user_id):
        if not reason:
            message.reply_text("Người dùng này đã bị cấm; Tôi muốn thay đổi lý do, nhưng bạn chưa cho tôi ...")
            return

        old_reason = sql.update_gban_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if old_reason:
            message.reply_text("Người dùng này đã bị cấm, vì lý do sau:\n"
                               "<code>{}</code>\n"
                               "Tôi đã đi và cập nhật nó với lý do mới của bạn!".format(html.escape(old_reason)),
                               parse_mode=ParseMode.HTML)
        else:
            message.reply_text("Người dùng này đã bị cấm, nhưng không có lý do nào được đặt ra; Tôi đã đi và cập nhật nó!")

        return

    message.reply_text("⚡️ **ĂN GẬY NHA CON** ⚡️")

    banner = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "<b>VBan</b>" \
                 "\n#VBAN" \
                 "\n<b>Status:</b> <code>Enforcing</code>" \
                 "\n<b>Sudo Admin:</b> {}" \
                 "\n<b>User:</b> {}" \
                 "\n<b>ID:</b> <code>{}</code>" \
                 "\n<b>Lý do:</b> {}".format(mention_html(banner.id, banner.first_name),
                                              mention_html(user_chat.id, user_chat.first_name), 
                                                           user_chat.id, reason or "Không có lý do"), 
                html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.kick_chat_member(chat_id, user_id)
        except BadRequest as excp:
            if excp.message in GBAN_ERRORS:
                pass
            else:
                message.reply_text("Could not vban due to: {}".format(excp.message))
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "Could not vban due to: {}".format(excp.message))
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, 
                  "{} đã bị bay màu!".format(mention_html(user_chat.id, user_chat.first_name)),
                html=True)
    message.reply_text("Person has been vbanned.")


@run_async
def ungban(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Bạn dường như không đề cập đến một người dùng!")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("Đó không phải là một người dùng!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("Người dùng này không bị cấm!")
        return

    banner = update.effective_user  # type: Optional[User]

    message.reply_text("Tôi xin lỗi {}, vô lạii nhóm với cơ hội thứ hai".format(user_chat.first_name))

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "<b>Regression of VBan</b>" \
                 "\n#UNGBAN" \
                 "\n<b>Status:</b> <code>Ceased</code>" \
                 "\n<b>Sudo Admin:</b> {}" \
                 "\n<b>User:</b> {}" \
                 "\n<b>ID:</b> <code>{}</code>".format(mention_html(banner.id, banner.first_name),
                                                       mention_html(user_chat.id, user_chat.first_name), 
                                                                    user_chat.id),
                 html=True)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'kicked':
                bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text("Could not un-gban due to: {}".format(excp.message))
                bot.send_message(OWNER_ID, "Could not un-gban due to: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, 
                  "{} đã được ân xá khỏi gban!".format(mention_html(user_chat.id, 
                                                                         user_chat.first_name)),
                  html=True)

    message.reply_text("Người này đã được bỏ cấm và được ân xá!")


@run_async
def gbanlist(bot: Bot, update: Update):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text("Không có bất kỳ người dùng nào bị cấm! Bạn tốt hơn tôi mong đợi...")
        return

    banfile = 'Vặn những kẻ này.\n'
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            banfile += "Lý do: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(document=output, filename="gbanlist.txt",
                                                caption="Đây là danh sách những người dùng bị cấm.")


def check_and_ban(update, user_id, should_message=True):
    if sql.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            update.effective_message.reply_text("Đây là người xấu, họ không nên ở đây!")


@run_async
def enforce_gban(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    if sql.does_chat_gban(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_ban(update, user.id)

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id, should_message=False)


@run_async
@user_admin
def gbanstat(bot: Bot, update: Update, args: List[str]):
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Tôi đã kích hoạt vbans trong nhóm này. Điều này sẽ giúp bảo vệ bạn "
                                                "từ những kẻ gửi thư rác, những nhân vật không đáng yêu và những kẻ troll lớn nhất.")
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text("Tôi đã tắt vbans trong nhóm này. GBans sẽ không ảnh hưởng đến người dùng của bạn "
                                                "nữa không. Bạn sẽ ít được bảo vệ khỏi bất kỳ kẻ troll và kẻ gửi thư rác nào "
                                                "nữa!")
    else:
        update.effective_message.reply_text("Hãy cho tôi một số đối số để chọn một thiết lập! on/off, yes/no!\n\n"
                                            "Cài đặt hiện tại của bạn là: {}\n"
                                            "Khi True, bất kỳ gbans nào xảy ra cũng sẽ xảy ra trong nhóm của bạn. "
                                            "Khi False, họ sẽ không, để lại cho bạn sự thương xót có thể có của "
                                            "spammers.".format(sql.does_chat_gban(update.effective_chat.id)))


def __stats__():
    return "{} gbanned users.".format(sql.num_gbanned_users())


def __user_info__(user_id):
    is_gbanned = sql.is_user_gbanned(user_id)

    text = "Bị cấm trên toàn cầu: <b>{}</b>"
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += "\nLý do: {}".format(html.escape(user.reason))
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "Trò chuyện này đang thực thi *vbans*: `{}`.".format(sql.does_chat_gban(chat_id))


__help__ = """
*Admin only:*
 - /setbaymau <on/off/yes/no>: Sẽ vô hiệu hóa ảnh hưởng của lệnh cấm toàn cầu đối với nhóm của bạn hoặc trả lại cài đặt hiện tại của bạn.

Gbans, còn được gọi là lệnh cấm toàn cầu, được chủ sở hữu bot sử dụng để cấm những người gửi thư rác trên tất cả các nhóm. Điều này giúp bảo vệ \
bạn và các nhóm của bạn bằng cách loại bỏ lũ spam càng nhanh càng tốt. Họ có thể bị tắt cho nhóm của bạn bằng cách gọi \
/setbaymau

- /tomau - Gỡ ban
- /baymau - Ban
- /listbaymau - Danh sách bay màu
"""

__mod_name__ = "Bay màu"

GBAN_HANDLER = CommandHandler("baymau", gban, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGBAN_HANDLER = CommandHandler("tomau", ungban, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GBAN_LIST = CommandHandler("listbaymau", gbanlist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GBAN_STATUS = CommandHandler("setbaymau", gbanstat, pass_args=True, filters=Filters.group)

GBAN_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gban)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
