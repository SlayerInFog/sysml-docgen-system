from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SysMLModel(Base):
    __tablename__ = "sysml_models"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, default=1)
    branch_name: Mapped[str] = mapped_column(String(80), default="main")
    version_tag: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="parsed")
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="models")
    uploaded_by_user = relationship("User", back_populates="uploaded_models")
    elements = relationship("ModelElement", back_populates="model", cascade="all, delete-orphan")
    relations = relationship("ModelRelation", back_populates="model", cascade="all, delete-orphan")
    documents = relationship("GeneratedDocument", back_populates="model")


class ModelElement(Base):
    __tablename__ = "model_elements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("sysml_models.id"), index=True)
    element_uid: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    type: Mapped[str] = mapped_column(String(80), index=True)
    documentation: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_uid: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    model = relationship("SysMLModel", back_populates="elements")


class ModelRelation(Base):
    __tablename__ = "model_relations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("sysml_models.id"), index=True)
    source_uid: Mapped[str] = mapped_column(String(255), index=True)
    target_uid: Mapped[str] = mapped_column(String(255), index=True)
    relation_type: Mapped[str] = mapped_column(String(80), index=True)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    model = relationship("SysMLModel", back_populates="relations")
