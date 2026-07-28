from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    items: Mapped[list["ClothingItem"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    name: Mapped[str] = mapped_column(String(120), default="")
    category: Mapped[str] = mapped_column(String(60), index=True)
    color: Mapped[str] = mapped_column(String(60), default="")
    material: Mapped[str] = mapped_column(String(60), default="")
    pattern: Mapped[str] = mapped_column(String(60), default="")
    style: Mapped[str] = mapped_column(String(60), default="")
    occasion: Mapped[str] = mapped_column(String(60), default="")
    season: Mapped[str] = mapped_column(String(60), default="")
    description: Mapped[str] = mapped_column(Text, default="")

    # Kategorienspezifische Details (z.B. {"schnitt": "slim", "waschung": "dark"})
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Bild direkt in der DB gespeichert
    image_data: Mapped[bytes] = mapped_column(LargeBinary)
    image_mime: Mapped[str] = mapped_column(String(60), default="image/jpeg")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    owner: Mapped["User"] = relationship(back_populates="items")
