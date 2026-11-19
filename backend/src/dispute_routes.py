from fastapi import APIRouter, Depends
from sqlalchemy import select
from .database import Session
from .security import current, allow
from .models import Claim, Machine
from .dispute_models import DisputeReceipt, SampleLabel, RiskScoring
from .dispute_schemas import ReceiptIn
from . import dispute_service as ds
router = APIRouter()

@router.get('/history-claims')
def history_claims(u=Depends(current)):
    # 常规 /claims 只列现场索赔；回执登记需要覆盖已结案的历史索赔
    with Session() as s:
        rows=s.execute(select(Claim.id,Claim.code,Claim.part,Claim.status,Machine.serial)
                       .join(Machine,Claim.machine_id==Machine.id)
                       .where(Claim.historical==True).order_by(Claim.id)).all()
        return [{'id':r.id,'code':r.code,'part':r.part,'status':r.status,
                 'machine_serial':r.serial,'historical':True} for r in rows]

@router.get('/dispute-receipts')
def receipts(u=Depends(current)):
    with Session() as s:
        return [ds.receipt_view(s, x) for x in s.scalars(
            select(DisputeReceipt).order_by(DisputeReceipt.claim_id, DisputeReceipt.revision_no.desc()))]

@router.post('/dispute-receipts')
def add_receipt(d: ReceiptIn, u=Depends(current)):
    allow(u, 'admin')  # 主管在分流页面登记带修订号的回执
    with Session.begin() as s:
        return ds.register(s, d, u)

@router.get('/sample-labels')
def labels(u=Depends(current)):
    with Session() as s:
        return [ds.label_view(s, x) for x in s.scalars(select(SampleLabel).order_by(SampleLabel.id))]

@router.get('/risk-scorings')
def scorings(u=Depends(current)):
    with Session() as s:
        return [ds.scoring_view(s, x) for x in s.scalars(select(RiskScoring).order_by(RiskScoring.id.desc()))]
