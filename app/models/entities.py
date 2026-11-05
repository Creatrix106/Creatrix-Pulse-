"""
SQLAlchemy 2.0 Declarative Models for PostgreSQL 15+ with asyncpg.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Integer,
    Float,
    BigInteger,
    Boolean,
    DateTime,
    Date,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="admin", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    datasets: Mapped[List["Dataset"]] = relationship("Dataset", back_populates="user", cascade="all, delete-orphan")
    reports: Mapped[List["Report"]] = relationship("Report", back_populates="user")

class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    capabilities: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    columns: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
    date_range: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB, nullable=True)
    filter_options: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=lambda: {"categories": [], "regions": []})
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    schema_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    started_at: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="datasets")
    rows: Mapped[List["DatasetRow"]] = relationship("DatasetRow", back_populates="dataset", cascade="all, delete-orphan")
    mappings: Mapped[List["DatasetMapping"]] = relationship("DatasetMapping", back_populates="dataset", cascade="all, delete-orphan")
    reports: Mapped[List["Report"]] = relationship("Report", back_populates="dataset", cascade="all, delete-orphan")

class DatasetRow(Base):
    __tablename__ = "dataset_rows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    order_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    transaction_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    product_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    customer_identifier: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="rows")

    __table_args__ = (
        Index("idx_dataset_rows_dataset_date", "dataset_id", "transaction_date"),
        Index("idx_dataset_rows_category", "dataset_id", "product_category"),
        Index("idx_dataset_rows_region", "dataset_id", "region"),
        Index("idx_dataset_rows_customer", "dataset_id", "customer_identifier"),
        Index("idx_dataset_rows_product", "dataset_id", "product_id"),
    )

class DatasetMapping(Base):
    __tablename__ = "dataset_mappings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    source_column: Mapped[str] = mapped_column(String(255), nullable=False)
    target_dimension: Mapped[str] = mapped_column(String(128), nullable=False)
    data_type: Mapped[str] = mapped_column(String(64), default="string", nullable=False)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="mappings")

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(50), default="csv", nullable=False)
    parameters: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    download_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="reports")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="reports")
