from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VersionBranch(Base):
    __tablename__ = "version_branches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    item_type: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_model_id: Mapped[int | None] = mapped_column(ForeignKey("sysml_models.id"), nullable=True, index=True)
    head_template_id: Mapped[int | None] = mapped_column(ForeignKey("document_templates.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="version_branches")
    head_model = relationship("SysMLModel", foreign_keys=[head_model_id])
    head_template = relationship("DocumentTemplate", foreign_keys=[head_template_id])
    creator = relationship("User", foreign_keys=[created_by])


class VersionTag(Base):
    __tablename__ = "version_tags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    item_type: Mapped[str] = mapped_column(String(20), index=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("version_branches.id"), nullable=True, index=True)
    model_id: Mapped[int | None] = mapped_column(ForeignKey("sysml_models.id"), nullable=True, index=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("document_templates.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="version_tags")
    branch = relationship("VersionBranch", foreign_keys=[branch_id])
    model = relationship("SysMLModel", foreign_keys=[model_id])
    template = relationship("DocumentTemplate", foreign_keys=[template_id])
    creator = relationship("User", foreign_keys=[created_by])


class VersionRollbackRecord(Base):
    __tablename__ = "version_rollback_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    item_type: Mapped[str] = mapped_column(String(20), index=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("version_branches.id"), index=True)
    tag_id: Mapped[int | None] = mapped_column(ForeignKey("version_tags.id"), nullable=True, index=True)
    target_model_id: Mapped[int | None] = mapped_column(ForeignKey("sysml_models.id"), nullable=True, index=True)
    new_model_id: Mapped[int | None] = mapped_column(ForeignKey("sysml_models.id"), nullable=True, index=True)
    target_template_id: Mapped[int | None] = mapped_column(ForeignKey("document_templates.id"), nullable=True, index=True)
    new_template_id: Mapped[int | None] = mapped_column(ForeignKey("document_templates.id"), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="version_rollback_records")
    branch = relationship("VersionBranch", foreign_keys=[branch_id])
    tag = relationship("VersionTag", foreign_keys=[tag_id])
    target_model = relationship("SysMLModel", foreign_keys=[target_model_id])
    new_model = relationship("SysMLModel", foreign_keys=[new_model_id])
    target_template = relationship("DocumentTemplate", foreign_keys=[target_template_id])
    new_template = relationship("DocumentTemplate", foreign_keys=[new_template_id])
    creator = relationship("User", foreign_keys=[created_by])
