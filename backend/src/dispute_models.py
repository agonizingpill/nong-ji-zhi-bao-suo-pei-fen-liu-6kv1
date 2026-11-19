from sqlalchemy import String, Integer, Boolean, ForeignKey, Text, JSON, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class DisputeReceipt(Base):
    # 争议回执只追加：同一索赔同一修订号仅一张，更正用更高修订号登记，不覆盖旧回执
    __tablename__='dispute_receipts'
    __table_args__=(UniqueConstraint('claim_id','revision_no',name='uk_receipt_claim_revision'),CheckConstraint('revision_no >= 1'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    claim_id:Mapped[int]=mapped_column(ForeignKey('claims.id'))
    revision_no:Mapped[int]=mapped_column(Integer)
    disputed:Mapped[bool]=mapped_column(Boolean)
    note:Mapped[str]=mapped_column(Text,default='')
    registered_by:Mapped[str]=mapped_column(String(120))
    received_at:Mapped[str]=mapped_column(String(40))

class SampleLabel(Base):
    # 评分受理时冻结的标签快照，每索赔至多一份；之后回执更正不改变这里
    __tablename__='sample_labels'
    __table_args__=(CheckConstraint('receipt_revision_no >= 1'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    claim_id:Mapped[int]=mapped_column(ForeignKey('claims.id'),unique=True)
    label:Mapped[int]=mapped_column(Integer)
    receipt_revision_no:Mapped[int]=mapped_column(Integer)
    receipt_id:Mapped[int]=mapped_column(ForeignKey('dispute_receipts.id'))
    frozen_at:Mapped[str]=mapped_column(String(40))

class RiskScoring(Base):
    # 每次评分一条，保留采用的标签清单；回执更正不重写既有评分
    __tablename__='risk_scorings'
    id:Mapped[int]=mapped_column(primary_key=True)
    claim_id:Mapped[int]=mapped_column(ForeignKey('claims.id'))
    risk:Mapped[float]=mapped_column()
    training_rows:Mapped[int]=mapped_column(Integer)
    holdout_rows:Mapped[int]=mapped_column(Integer)
    sample_size:Mapped[int]=mapped_column(Integer)
    metrics:Mapped[dict]=mapped_column(JSON)
    label_manifest:Mapped[list]=mapped_column(JSON)
    created_at:Mapped[str]=mapped_column(String(40))
