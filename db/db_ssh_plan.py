from sqlalchemy.orm.session import Session
from db.models import DbSshPlan
from schemas import SshPlan, PlanStatusDb
from sqlalchemy import and_
from typing import List


def __get_attrs(**kwargs):

    dic_attrs = {
        'plan_id': DbSshPlan.plan_id,
        'limit': DbSshPlan.limit,
        'price': DbSshPlan.price,
        'traffic': DbSshPlan.traffic,
        'duration': DbSshPlan.duration,
        'status': DbSshPlan.status
    }
    prepar_attrs = []
    for item, value in kwargs.items():
        if item in dic_attrs:
            prepar_attrs.append(dic_attrs[item] == value)

    return prepar_attrs


def create_plan(request: SshPlan, db: Session) -> DbSshPlan:
    
    service = DbSshPlan(
        limit= request.limit,
        price= request.price,
        traffic= request.traffic,
        duration= request.duration,
        status= request.status
    )
    
    db.add(service)
    db.commit()
    db.refresh(service)

    return service


def get_plans_by_attrs(db: Session, **kwargs) -> List[DbSshPlan]:

    attrs = __get_attrs(**kwargs)
    return db.query(DbSshPlan).filter(and_(*attrs)).all()


def get_all_plan(db: Session, status: PlanStatusDb= None) -> List[DbSshPlan]:

    if status:
        return db.query(DbSshPlan).filter(DbSshPlan.status == status).all()
    
    else:
        return db.query(DbSshPlan).all()


def get_plan_by_id(plan_id , db: Session) -> DbSshPlan:

    return db.query(DbSshPlan).filter(DbSshPlan.plan_id == plan_id ).first()

    
def change_status(plan_id, new_status: PlanStatusDb, db: Session, commit=True):
    
    service = db.query(DbSshPlan).filter(DbSshPlan.plan_id == plan_id )

    service.update({DbSshPlan.status: new_status})
    if commit:
        db.commit()

    return service
