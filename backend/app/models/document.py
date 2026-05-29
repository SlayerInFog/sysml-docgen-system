from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentTemplate(Base):
    __tablename__ = "document_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(LONGTEXT().with_variant(Text, "sqlite"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    branch_name: Mapped[str] = mapped_column(String(80), default="main")
    version_tag: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="templates")
    documents = relationship("GeneratedDocument", back_populates="template")
    versions = relationship("DocumentTemplateVersion", back_populates="template", cascade="all, delete-orphan")


class DocumentTemplateVersion(Base):
    __tablename__ = "document_template_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("document_templates.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(LONGTEXT().with_variant(Text, "sqlite"))
    branch_name: Mapped[str] = mapped_column(String(80), default="main")
    version_tag: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    template = relationship("DocumentTemplate", back_populates="versions")
    created_by_user = relationship("User")


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("sysml_models.id"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("document_templates.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(30), default="success")
    html_content: Mapped[str] = mapped_column(LONGTEXT().with_variant(Text, "sqlite"))
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="documents")
    model = relationship("SysMLModel", back_populates="documents")
    template = relationship("DocumentTemplate", back_populates="documents")
    created_by_user = relationship("User", back_populates="generated_documents")
