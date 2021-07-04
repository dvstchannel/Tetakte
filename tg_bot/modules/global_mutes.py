import html
from io import BytesIO
from typing import Optional, List

from telegram import Message, Update, Bot, User, Chat
from telegram.error import BadRequest, TelegramError
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.global_mutes_sql as sql
from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, STRICT_GMUTE
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.misc import send_to_list
from tg_bot.modules.sql.users_sql import get_all_chats

GMUTE_ENFORCE_GROUP = 6


@run_async
def gmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bạn chưa chỉ định cho tôi sẽ đồ sát người nào?.")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Tôi theo dõi, bằng con mắt nhỏ của mình ... một cuộc chiến tranh dành cho người dùng sudo! Tại sao các bạn lại bật nhau?")
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text("OOOH ai đó đang cố bịt miệng người dùng hỗ trợ! *lấy bỏng ngô*")
        return

    if user_id == bot.id:
        message.reply_text("-_- Thật buồn cười, hãy tự câm miệng tại sao tôi lại không? Rất vui.")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != 'private':
        message.reply_text("Đó không phải là một người dùng!")
        return

    if sql.is_user_gmuted(user_id):
        if not reason:
            message.reply_text("Người dùng này đã bị khóa mõm; Tôi muốn thay đổi lý do, nhưng bạn chưa đưa cho tôi một lý do...")
            return

        success = sql.update_gmute_reason(user_id, user_chat.username or user_chat.first_name, reason)
        if success:
            message.reply_text("Người dùng này đã bị khóa mõm; Tôi đã đi và cập nhật lý do gmute!")
        else:
            message.reply_text("Bạn có phiền thử lại không? Tôi nghĩ rằng người này đã bị tắt tiếng, nhưng sau đó họ không?"
                               "Tôi rất bối rối")

        return

    message.reply_text("*đang lấy cuộn băng keo* 😉")

    muter = update.effective_user  # type: Optional[User]
    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} đã bị khóa mõm {} "
                 "because:\n{}".format(mention_html(muter.id, muter.first_name),
                                       mention_html(user_chat.id, user_chat.first_name), reason or "No reason given"),
                 html=True)

    sql.gmute_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gmutes
        if not sql.does_chat_gmute(chat_id):
            continue

        try:
            bot.restrict_chat_member(chat_id, user_id, can_send_messages=False)
        except BadRequest as excp:
            if excp.message == "User is an administrator of the chat":
                pass
            elif excp.message == "Chat not found":
                pass
            elif excp.message == "Not enough rights to restrict/unrestrict chat member":
                pass
            elif excp.message == "User_not_participant":
                pass
            elif excp.message == "Peer_id_invalid":  # Suspect this happens when a group is suspended by telegram.
                pass
            elif excp.message == "Group chat was deactivated":
                pass
            elif excp.message == "Need to be inviter of a user to kick it from a basic group":
                pass
            elif excp.message == "Chat_admin_required":
                pass
            elif excp.message == "Only the creator of a basic group can kick group administrators":
                pass
            elif excp.message == "Method is available only for supergroups":
                pass
            elif excp.message == "Can't demote chat creator":
                pass
            else:
                message.reply_text("Không thể tắt tiếng do:: {}".format(excp.message))
                send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "Không thể tắt tiếng do: {}".format(excp.message))
                sql.ungmute_user(user_id)
                return
        except TelegramError:
            pass

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "gmute hoàn thành!")
    message.reply_text("Một người đã bị tắt tiếng.")


@run_async
def ungmute(bot: Bot, update: Update, args: List[str]):
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Bạn dường như không đề cập đến một người dùng.")
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != 'private':
        message.reply_text("Đó không phải là một người dùng!")
        return

    if not sql.is_user_gmuted(user_id):
        message.reply_text("Người dùng này không bị tắt tiếng!")
        return

    muter = update.effective_user  # type: Optional[User]

    message.reply_text("Tôi sẽ cho phép {} nói lại, trên toàn bộ nhóm của tôi!".format(user_chat.first_name))

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS,
                 "{} đã tắt khóa mõm cho {}".format(mention_html(muter.id, muter.first_name),
                                                   mention_html(user_chat.id, user_chat.first_name)),
                 html=True)

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat.chat_id

        # Check if this group has disabled gmutes
        if not sql.does_chat_gmute(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == 'restricted':
                bot.restrict_chat_member(chat_id, int(user_id),
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)

        except BadRequest as excp:
            if excp.message == "User is an administrator of the chat":
                pass
            elif excp.message == "Chat not found":
                pass
            elif excp.message == "Not enough rights to restrict/unrestrict chat member":
                pass
            elif excp.message == "User_not_participant":
                pass
            elif excp.message == "Method is available for supergroup and channel chats only":
                pass
            elif excp.message == "Not in the chat":
                pass
            elif excp.message == "Channel_private":
                pass
            elif excp.message == "Chat_admin_required":
                pass
            else:
                message.reply_text("Không thể bỏ tắt tiếng do: {}".format(excp.message))
                bot.send_message(OWNER_ID, "Không thể bỏ tắt tiếng do: {}".format(excp.message))
                return
        except TelegramError:
            pass

    sql.ungmute_user(user_id)

    send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "hoàn thành un-gmute!")

    message.reply_text("Một người đã được bỏ GMute.")


@run_async
def gmutelist(bot: Bot, update: Update):
    muted_users = sql.get_gmute_list()

    if not muted_users:
        update.effective_message.reply_text("Không có bất kỳ người dùng bị tắt tiếng nào! Bạn tốt hơn tôi mong đợi...")
        return

    mutefile = 'Vặn những kẻ này.\n'
    for user in muted_users:
        mutefile += "[x] {} - {}\n".format(user["name"], user["user_id"])
        if user["reason"]:
            mutefile += "Lý do: {}\n".format(user["reason"])

    with BytesIO(str.encode(mutefile)) as output:
        output.name = "gmutelist.txt"
        update.effective_message.reply_document(document=output, filename="gmutelist.txt",
                                                caption="Đây là danh sách những người dùng hiện đang bị ẩn.")


def check_and_mute(bot, update, user_id, should_message=True):
    if sql.is_user_gmuted(user_id):
        bot.restrict_chat_member(update.effective_chat.id, user_id, can_send_messages=False)
        if should_message:
            update.effective_message.reply_text("Đây là một người xấu, tôi sẽ im lặng họ cho bạn!")


@run_async
def enforce_gmute(bot: Bot, update: Update):
    # Not using @restrict handler to avoid spamming - just ignore if cant gmute.
    if sql.does_chat_gmute(update.effective_chat.id) and update.effective_chat.get_member(bot.id).can_restrict_members:
        user = update.effective_user  # type: Optional[User]
        chat = update.effective_chat  # type: Optional[Chat]
        msg = update.effective_message  # type: Optional[Message]

        if user and not is_user_admin(chat, user.id):
            check_and_mute(bot, update, user.id, should_message=True)
        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_mute(bot, update, mem.id, should_message=True)
        if msg.reply_to_message:
            user = msg.reply_to_message.from_user  # type: Optional[User]
            if user and not is_user_admin(chat, user.id):
                check_and_mute(bot, update, user.id, should_message=True)

@run_async
@user_admin
def gmutestat(bot: Bot, update: Update, args: List[str]):
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gmutes(update.effective_chat.id)
            update.effective_message.reply_text("Tôi đã bật gmutes trong nhóm này. Điều này sẽ giúp bảo vệ bạn "
                                                "từ những người gửi thư rác, ký tự không có mùi và lũ cặn bã.")
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gmutes(update.effective_chat.id)
            update.effective_message.reply_text("Tôi đã tắt gmutes trong nhóm này. GMutes sẽ không ảnh hưởng đến người dùng của bạn "
                                                "nữa không. Tuy nhiên, bạn sẽ ít được bảo vệ khỏi lũ cặn bã hơn!")
    else:
        update.effective_message.reply_text("Hãy cho tôi một số đối số để chọn một thiết lập! on/off, yes/no!\n\n"
                                            "Cài đặt hiện tại của bạn là: {}\n"
                                            "Khi True, bất kỳ gmutes nào xảy ra cũng sẽ xảy ra trong nhóm của bạn. "
                                            "Khi False, họ sẽ không, bỏ mặc bạn với sự thương xót có thể "
                                            "spammers.".format(sql.does_chat_gmute(update.effective_chat.id)))


def __stats__():
    return "{} đã bị khóa mõm.".format(sql.num_gmuted_users())


def __user_info__(user_id):
    is_gmuted = sql.is_user_gmuted(user_id)

    text = "Tắt tiếng toàn cầu: <b>{}</b>"
    if is_gmuted:
        text = text.format("Yes")
        user = sql.get_gmuted_user(user_id)
        if user.reason:
            text += "\nLý do: {}".format(html.escape(user.reason))
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "Cuộc trò chuyện này đang thực thi *gmutes*: `{}`.".format(sql.does_chat_gmute(chat_id))


__help__ = """
*Admin only:*
 - /gmutestat <on/off/yes/no>: Sẽ vô hiệu hóa ảnh hưởng của tắt tiếng toàn cầu đối với nhóm của bạn hoặc trả lại cài đặt hiện tại của bạn.
Gmutes, còn được gọi là tắt tiếng toàn cầu, được chủ sở hữu bot sử dụng để tắt tiếng những người gửi spam trên tất cả các nhóm. Điều này giúp bảo vệ \
bạn và các nhóm của bạn bằng cách loại bỏ lũ spam càng nhanh càng tốt. Họ có thể bị tắt cho nhóm của bạn bằng cách gọi \
/gmutestat
"""

__mod_name__ = "GMute"

GMUTE_HANDLER = CommandHandler("gmute", gmute, pass_args=True,
                              filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
UNGMUTE_HANDLER = CommandHandler("ungmute", ungmute, pass_args=True,
                                filters=CustomFilters.sudo_filter | CustomFilters.support_filter)
GMUTE_LIST = CommandHandler("gmutelist", gmutelist,
                           filters=CustomFilters.sudo_filter | CustomFilters.support_filter)

GMUTE_STATUS = CommandHandler("gmutestat", gmutestat, pass_args=True, filters=Filters.group)

GMUTE_ENFORCER = MessageHandler(Filters.all & Filters.group, enforce_gmute)

dispatcher.add_handler(GMUTE_HANDLER)
dispatcher.add_handler(UNGMUTE_HANDLER)
dispatcher.add_handler(GMUTE_LIST)
dispatcher.add_handler(GMUTE_STATUS)

if STRICT_GMUTE:
    dispatcher.add_handler(GMUTE_ENFORCER, GMUTE_ENFORCE_GROUP)
