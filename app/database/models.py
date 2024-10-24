from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, update, ForeignKey
from datetime import datetime
import uuid
from sqlalchemy.future import select
from typing import Dict, Any
import sys
from sqlalchemy.orm import relationship


sys.path.append("..")

from app.logger import RequestSpan
from .database import Base, DatabaseException


class User(Base):
    __tablename__ = "users"

    # Unique identifier
    id = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )

    # email
    email = Column(String, unique=True, nullable=False)

    # timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @staticmethod
    async def create(
        email: str, session: AsyncSession, span: RequestSpan | None = None
    ):
        try:
            user = User(email=email)
            session.add(user)
            await session.flush()
            return user
        except Exception as e:
            if span:
                span.error(f"database::models::User::create: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e

    @staticmethod
    async def read(id: str, session: AsyncSession, span: RequestSpan | None = None):
        try:
            result = await session.execute(select(User).filter_by(id=id))
            return result.scalars().first()
        except Exception as e:
            if span:
                span.error(f"database::models::User::read: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e

    @staticmethod
    async def read_by_email(
        email: str, session: AsyncSession, span: RequestSpan | None = None
    ):
        try:
            result = await session.execute(select(User).filter_by(email=email))
            return result.scalars().first()
        except Exception as e:
            if span:
                span.error(f"database::models::User::read_by_email: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e


class Om(Base):
    __tablename__ = "oms"

    id = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )

    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    upload_id = Column(String, nullable=False)

    title = Column(String, nullable=False)

    description = Column(String, nullable=True)

    summary = Column(String, nullable=True)

    # timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    async def create(
        user_id: str,
        upload_id: str,
        title: str,
        description: str,
        summary: str,
        session: AsyncSession,
        span: RequestSpan | None = None,
    ):
        try:
            om = Om(
                user_id=user_id,
                upload_id=upload_id,
                title=title,
                description=description,
                summary=summary,
            )
            session.add(om)
            await session.flush()
            return om
        except Exception as e:
            if span:
                span.error(f"database::models::Om::create: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e

    @staticmethod
    async def read(id: str, session: AsyncSession, span: RequestSpan | None = None):
        result = await session.execute(select(Om).filter_by(id=id))
        return result.scalars().first()

    @staticmethod
    async def update(
        id: str,
        update_data: Dict[str, Any],
        session: AsyncSession,
        span: RequestSpan | None = None,
    ):
        try:
            # First, check if the Om exists
            result = await session.execute(select(Om).filter_by(id=id))
            om = result.scalars().first()
            if not om:
                raise ValueError(f"Om with id {id} not found")

            # Update the Om
            stmt = update(Om).where(Om.id == id).values(**update_data).returning(Om)
            result = await session.execute(stmt)
            updated_om = result.scalars().first()
            if not updated_om:
                raise ValueError(f"Om with id {id} not found")
            await session.commit()
            return updated_om
        except Exception as e:
            if span:
                span.error(f"database::models::Om::update: {e}")
            db_e = DatabaseException.from_sqlalchemy_error(e)
            raise db_e

    @staticmethod
    async def update_summary(
        id: str, summary: str, session: AsyncSession, span: RequestSpan | None = None
    ):
        return await Om.update(id, {"summary": summary}, session, span)

    @classmethod
    async def read_by_user_id(
        cls, user_id: str, session: AsyncSession, span: RequestSpan
    ):
        query = select(cls).where(cls.user_id == user_id)
        result = await session.execute(query)
        return result.scalars().all()


# class Chat(Base):
#     __tablename__ = "chat"

#     # Unique identifier
#     id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)

#     user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)

#     telegram_user_id = Column(Integer, nullable=False, unique=True)
#     telegram_chat_id = Column(Integer, nullable=False, unique=True)

#     conversations = relationship("Conversation", back_populates="chat")

#     # timestamps
#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#     @staticmethod
#     async def create(
#         user_id,
#         message: telebot_types.Message,
#         session,
#         span=None
#     ):
#         """
#         Create a new chat.
#         """
#         try:
#             chat = Chat(
#                 user_id=user_id,
#                 telegram_user_id=message.from_user.id,
#                 telegram_chat_id=message.chat.id,
#             )
#             session.add(chat)
#             await session.flush()
#             return chat
#         except Exception as e:
#             if span:
#                 span.error(f"Chat::create(): Error creating chat: {e}")
#             e = DatabaseException.from_sqlalchemy_error(e)
#             raise e

# # TODO: this might be able to do inside the state machine
# class ConversationState(PyEnum):
#     active = "active"
#     inactive = "inactive"
#     complete = "complete"

# class Conversation(Base):
#     __tablename__ = "conversations"

#     id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)

#     # Id of the chat the conversation belongs to
#     chat_id = Column(String ForeignKey("chats.id"), nullable=False)
#     chat = relationship("Chat", back_populates="conversations")

#     # ['active', 'inactive', 'complete']
#     state = Column(Enum(ConversationState))

#     # The messages within the conversation
#     messages = relationship("Message", backref="conversation")

#     # timestamps
#     created_at = Column(DateTime, default=datetime.utcnow)
#     updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


#     @staticmethod
#     async def active(chat_id, session, span=None):
#         """
#         Get the active conversation of a chat, or none if there is no such conversations

#         """

#         try:
#             conversation = await session.execute(
#                 select(Conversation).filter(
#                     Conversation.chat.id == chat_id, Conversation.state == "active"
#                 )
#             )
#             conversation = conversation.scalars().first()

#             return conversation
#         except Exception as e:
#             if span:
#                 span.error(
#                     f"Conversation::active(): Error getting active conversation: {e}"
#                 )
#             e = DatabaseException.from_sqlalchemy_error(e)
#             raise e

#     @staticmethod
#     async def create(
#         chat_id, session, span=None):
#         """
#         Create a new conversation. If there is already an active conversation, return None

#         chat_id: The chat ID to start the conversation with
#         agenda: The agenda for the conversation
#         span: The span to use for tracing. If None, no tracing is done

#         Returns:
#         - The conversation if the conversation was successfully started. None otherwise
#         Exceptions:
#         - If there is an error creating the conversation
#         """
#         try:
#             # Check if there is an active conversation
#             # If there is, return None

#             active_conversation = await Conversation.active(chat_id, session, span)
#             if active_conversation:
#                 return None
#             new_conversation = Conversation(
#                 chat_id=chat_id,
#                 state="active",
#                 created_at=datetime.datetime.now(),
#                 updated_at=datetime.datetime.now(),
#             )

#             session.add(new_conversation)

#             # Flush so the conversation is created and we can get the ID
#             # within the same session
#             await session.flush()

#             if span:
#                 span.info(
#                     f"Conversation::create(): Starting new conversation for chat {chat_id} | conversation_id: {new_conversation.id}"
#                 )

#             return new_conversation
#         except Exception as e:
#             if span:
#                 span.error(f"Conversation::create(): Error creating conversation: {e}")
#             e = DatabaseException.from_sqlalchemy_error(e)
#             raise e

#     @staticmethod
#     async def read(conversation_id, session, span=None):
#         try:
#             conversation = await session.execute(
#                 select(Conversation).filter(
#                     Conversation.id == conversation_id,
#                 )
#             )
#             conversation = conversation.scalars().first()
#             return conversation
#         except Exception as e:
#             if span:
#                 span.error(f"Conversation::read(): Error getting conversation: {e}")
#             e = DatabaseException.from_sqlalchemy_error(e)
#             raise e

#     @staticmethod
#     async def read_all_from_chat(chat_id, session, span=None):
#         try:
#             conversations = await session.execute(
#                 select(Conversation).filter(Conversation.chat_id == chat_id)
#             )
#             conversations = conversations.scalars().all()
#             return conversations
#         except Exception as e:
#             if span:
#                 span.error(
#                     f"Conversation::read_all(): Error getting conversations: {e}"
#                 )
#             e = DatabaseException.from_sqlalchemy_error(e)
#             raise e

#     @staticmethod
#     async def update_state(conversation_id, state, session, span=None):
#         try:
#             conversation = await session.execute(
#                 select(Conversation).filter(
#                     Conversation.id == conversation_id,
#                 )
#             )
#             conversation = conversation.scalars().first()
#             if not conversation:
#                 return None
#             conversation.state = state
#             conversation.updated_at = datetime.datetime.now()
#             await session.flush()
#         except Exception as e:
#             if span:
#                 span.error(
#                     f"Conversation::update_state() - Error updating conversation state: {e}"
#                 )
#             e = DatabaseException.from_sqlalchemy_error(e)
#             raise e

# class Message(Base):
#     __tablename__ = "messages"

#     # id and the messages chat.id are unique together, as are its id and conversation_id

#     # Unique identifier
#     id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False)

#     telegram_message_id = Column(Integer, nullable=False, unique=True)

#     # The conveursation this message belongs to
#     conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)

#     # whether or not this is a message or a response
#     is_response = Column(Boolean, default=False)

#     # Message replies (if any)
#     reply_to_message_id = Column(Integer, ForeignKey("messages.telegram_message_id"), nullable=True)
#     reply_to_message = relationship("Message", remote_side=[telegram_message_id], backref="replies")

#     text = Column(String)

#     timestamp = Column(DateTime)

#     __table_args__ = (UniqueConstraint("id", "conversation_id"),)

#     @staticmethod
#     async def record(
#         conversation_id,
#         message: telebot_types.Message,
#         session,
#         is_response=False,
#         reply_to_message_id=None,
#         use_edit_date=False,
#         span=None,
#     ):
#         """
#         Add a message to the active conversation for the given chat.

#         message: The message to add
#         reply_to_message_id: The ID of the message that this message is a reply to
#         span: The span to use for tracing. If None, no tracing is done
#         """

#         try:
#             reply_to_message_id = reply_to_message_id or (
#                 message.reply_to_message.message_id
#                 if message.reply_to_message
#                 else None
#             )

#             new_message = Message(
#                 telegram_message_id=message.message_id,
#                 conversation_id=conversation_id,
#                 is_response=is_response,
#                 reply_to_message_id=reply_to_message_id,
#                 text=message.text,
#                 timestamp=datetime.datetime.fromtimestamp(
#                     message.edit_date if use_edit_date else message.date
#                 ),
#             )
#             session.add(new_message)
#             await session.flush()
#             return new_message
#         except Exception as e:
#             if span:
#                 span.error(f"Message::record(): Error adding message: {e}")
#             raise e

#     @staticmethod
#     async def read_all(conversation_id, session, limit=None, span=None):
#         try:
#             # TODO: not sure if and how i need to fix this
#             base_query = (
#                 select(Message)
#                 # .options(joinedload(Message.from_user))
#                 # .options(
#                 #     joinedload(Message.reply_to_message).joinedload(Message.from_user)
#                 # )
#                 .filter(Message.conversation_id == conversation_id)
#             )

#             if limit:
#                 base_query = base_query.limit(limit)

#             messages = await session.execute(
#                 base_query.order_by(Message.timestamp.desc())
#             )
#             messages = messages.scalars().all()

#             await session.flush()

#             return messages
#         except Exception as e:
#             if span:
#                 span.error(f"Message::read_all(): Error reading message: {e}")
#             e = DatabaseException.from_sqlalchemy_error(e)
#             raise e
