from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from .dispute_models import DisputeReceipt, SampleLabel, RiskScoring
from .models import Claim, Machine
from .claim_service import obj, audit

def now(): return datetime.now(timezone.utc).isoformat()

def receipt_view(s, x):
    return obj(x) | {'claim_code': s.get(Claim, x.claim_id).code,
                     'machine_serial': s.get(Machine, s.get(Claim, x.claim_id).machine_id).serial}

def label_view(s, x):
    c = s.get(Claim, x.claim_id)
    return obj(x) | {'claim_code': c.code, 'machine_serial': s.get(Machine, c.machine_id).serial}

def register(s, d, u):
    c = s.get(Claim, d.claim_id)
    if not c: raise HTTPException(404, '索赔记录不存在')
    # 同修订号重复登记直接拒绝：只留一张，重试不新增样本
    if s.scalar(select(DisputeReceipt.id).where(DisputeReceipt.claim_id == d.claim_id,
                                                DisputeReceipt.revision_no == d.revision_no)):
        raise HTTPException(409, f'修订号 {d.revision_no} 的回执已登记，重复登记不会新增样本')
    x = DisputeReceipt(claim_id=d.claim_id, revision_no=d.revision_no, disputed=d.disputed,
                       note=d.note, registered_by=u['email'], received_at=now())
    s.add(x); s.flush()
    audit(s, u, 'dispute_receipt_registered', f'{c.code}:rev{d.revision_no}:{int(d.disputed)}')
    return receipt_view(s, x)

def freeze_labels(s):
    # 评分受理时一次性冻结：仅对有回执且尚未入样的索赔，取当时最高修订号
    existing = {v.claim_id for v in s.scalars(select(SampleLabel)).all()}
    candidates = s.scalars(select(DisputeReceipt.claim_id).distinct()).all()
    for cid in candidates:
        if cid in existing: continue
        c = s.get(Claim, cid)
        if not c: continue
        s.refresh(c, with_for_update=True)
        if s.scalar(select(SampleLabel.id).where(SampleLabel.claim_id == cid)): continue
        top = s.scalar(select(DisputeReceipt).where(DisputeReceipt.claim_id == cid)
                       .order_by(DisputeReceipt.revision_no.desc()).limit(1))
        if not top: continue
        s.add(SampleLabel(claim_id=cid, label=int(top.disputed),
                          receipt_revision_no=top.revision_no, receipt_id=top.id, frozen_at=now()))
        s.flush()

def manifest(s):
    rows = s.scalars(select(SampleLabel).order_by(SampleLabel.id)).all()
    return [{'claim_code': s.get(Claim, v.claim_id).code, 'label': v.label,
             'revision_no': v.receipt_revision_no} for v in rows]

def record_scoring(s, claim, risk, metrics, manifest_rows):
    x = RiskScoring(claim_id=claim.id, risk=risk, training_rows=metrics['training_rows'],
                    holdout_rows=metrics['holdout_rows'], sample_size=len(manifest_rows),
                    metrics=metrics, label_manifest=manifest_rows, created_at=now())
    s.add(x); s.flush(); return x

def scoring_view(s, x):
    return obj(x) | {'claim_code': s.get(Claim, x.claim_id).code}
