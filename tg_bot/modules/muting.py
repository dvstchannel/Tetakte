import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

from tg_bot import dispatcher, LOGGER
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin, can_restrict
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable


@run_async
@bot_admin
@user_admin
@loggable
def mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Bạn sẽ cần cung cấp cho tôi tên người dùng để tắt tiếng hoặc trả lời một người nào đó để tắt tiếng.")
        return ""

    if user_id == bot.id:
        message.reply_text("Tôi không tự tắt tiếng!")
        return ""

    member = chat.get_member(int(user_id))

    if member:
        if is_user_admin(chat, user_id, member=member):
            message.reply_text("Sợ rằng tôi không thể ngăn một quản trị viên nói chuyện!")

        elif member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, can_send_messages=False)
            message.reply_text("👍🏻 Khóa mõm chi thuật 🤐")
            return "<b>{}:</b>" \
                   "\n#MUTE" \
                   "\n<b>Admin:</b> {}" \
                   "\n<b>User:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name))

        else:
            message.reply_text("Người dùng này đã bị tắt tiếng!")
    else:
        message.reply_text("Người dùng này không có trong cuộc trò chuyện!")

    return ""


@run_async
@bot_admin
@user_admin
@loggable
def unmute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Bạn sẽ cần cung cấp cho tôi tên người dùng để hiển thị hoặc trả lời một người nào đó để được hiển thị.")
        return ""

    member = chat.get_member(int(user_id))

    if member.status != 'kicked' and member.status != 'left':
        if member.can_send_messages and member.can_send_media_messages \
                and member.can_send_other_messages and member.can_add_web_page_previews:
            message.reply_text("This user already has the right to speak.")
        else:
            bot.restrict_chat_member(chat.id, int(user_id),
                                     can_send_messages=True,
                                     can_send_media_messages=True,
                                     can_send_other_messages=True,
                                     can_add_web_page_previews=True)
            message.reply_text("Unmuted!")
            return "<b>{}:</b>" \
                   "\n#UNMUTE" \
                   "\n<b>Admin:</b> {}" \
                   "\n<b>User:</b> {}".format(html.escape(chat.title),
                                              mention_html(user.id, user.first_name),
                                              mention_html(member.user.id, member.user.first_name))
    else:
        message.reply_text("Người dùng này thậm chí không tham gia cuộc trò chuyện, việc bật tiếng họ sẽ không khiến họ nói nhiều hơn họ "
                           "đã làm!")

    return ""


@run_async
@bot_admin
@can_restrict
@user_admin
@loggable
def temp_mute(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bạn dường như không đề cập đến một người dùng.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Tôi dường như không thể tìm thấy người dùng này")
            return ""
        else:
            raise

    if is_user_admin(chat, user_id, member):
        message.reply_text("I really wish I could mute admins...")
        return ""

    if user_id == bot.id:
        message.reply_text("Tôi sẽ không tự MUTE, bạn có điên không?")
        return ""

    if not reason:
        message.reply_text("Bạn chưa chỉ định thời gian để tắt tiếng người dùng này!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP MUTED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {}" \
          "\n<b>Time:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name), time_val)
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        if member.can_send_messages is None or member.can_send_messages:
            bot.restrict_chat_member(chat.id, user_id, until_date=mutetime, can_send_messages=False)
            message.reply_text("Câm miệng! 😠 Khóa mõm trong {}!".format(time_val))
            return log
        else:
            message.reply_text("Người dùng này đã bị tắt tiếng.")

    except BadRequest as excp:
        if excp.message == "Trả lời tin nhắn không tìm thấy":
            # Do not reply
            message.reply_text("Câm miệng! 😠 Khóa mõm trong {}!".format(time_val), quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR muting user %s in chat %s (%s) due to %s", user_id, chat.title, chat.id,
                             excp.message)
            message.reply_text("Chết tiệt, tôi không thể tắt tiếng người dùng đó.")

    return ""


__help__ = """
*Admin only:*
 - /diemhuyet <userhandle>: người dùng im lặng. Cũng có thể được sử dụng như một câu trả lời, tắt tiếng người dùng đã trả lời.
 - /tamdiemhuyet <userhandle> x(m/h/d): tắt tiếng người dùng trong x thời gian. (thông qua tay cầm, hoặc trả lời). m = phút, h = giờ, d = ngày.
 - /giaihuyet <userhandle>: bật tiếng người dùng. Cũng có thể được sử dụng như một câu trả lời, tắt tiếng người dùng đã trả lời.
"""

__mod_name__ = "Điểm huyệt"

MUTE_HANDLER = CommandHandler("diemhuyet", mute, pass_args=True, filters=Filters.group)
UNMUTE_HANDLER = CommandHandler("giaihuyet", unmute, pass_args=True, filters=Filters.group)
TEMPMUTE_HANDLER = CommandHandler(["tamdiemhuyet", "tmute"], temp_mute, pass_args=True, filters=Filters.group)

dispatcher.add_handler(MUTE_HANDLER)
dispatcher.add_handler(UNMUTE_HANDLER)
dispatcher.add_handler(TEMPMUTE_HANDLER)
