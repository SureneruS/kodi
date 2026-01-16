import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def generate_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Flag(Base):
    __tablename__ = "kodi_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    tenant_overrides: Mapped[list["TenantFlag"]] = relationship(
        back_populates="flag", cascade="all, delete-orphan"
    )
    user_overrides: Mapped[list["UserFlag"]] = relationship(
        back_populates="flag", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Flag {self.name}={self.enabled}>"


class TenantFlag(Base):
    __tablename__ = "kodi_tenant_flags"
    __table_args__ = (UniqueConstraint("flag_id", "tenant_id", name="uq_tenant_flag"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    flag_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("kodi_flags.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    flag: Mapped["Flag"] = relationship(back_populates="tenant_overrides")

    def __repr__(self) -> str:
        return f"<TenantFlag {self.flag_id}@{self.tenant_id}={self.enabled}>"


class UserFlag(Base):
    __tablename__ = "kodi_user_flags"
    __table_args__ = (
        UniqueConstraint("flag_id", "tenant_id", "user_id", name="uq_user_flag"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_id)
    flag_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("kodi_flags.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    flag: Mapped["Flag"] = relationship(back_populates="user_overrides")

    def __repr__(self) -> str:
        return f"<UserFlag {self.flag_id}@{self.tenant_id}/{self.user_id}={self.enabled}>"


class SchemaVersion(Base):
    __tablename__ = "kodi_schema_version"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
