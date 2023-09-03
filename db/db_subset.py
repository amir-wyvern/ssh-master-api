from sqlalchemy.orm.session import Session
from db.models import DbSubsetProfit
from schemas import (
    CreateSubsetProfit
)
from typing import List

def create_subset(request: CreateSubsetProfit, db: Session) -> DbSubsetProfit:
    
    subset = DbSubsetProfit(
        user_id= request.user_id,
        not_released_profit= request.not_released_profit,
        total_profit= request.total_profit,
        number_of_configs= request.number_of_configs,
    )

    db.add(subset)

    db.commit()
    db.refresh(subset)

    return subset


def get_subset_by_user(user_id: int, db: Session) -> DbSubsetProfit:
    
    return db.query(DbSubsetProfit).filter(DbSubsetProfit.user_id == user_id ).first()


def update_subset_by_user(user_id: int, new_not_released_profit: int, db: Session, commit= True) :

    subset = db.query(DbSubsetProfit).filter(DbSubsetProfit.user_id == user_id )

    subset.update({DbSubsetProfit.not_released_profit: new_not_released_profit})
    
    if commit:
        db.commit()
    
    return subset


def increase_not_released_profit_by_user(user_id: int, value :float, db: Session, commit= True) :

    subset = db.query(DbSubsetProfit).filter(DbSubsetProfit.user_id == user_id )

    subset.update({
        DbSubsetProfit.not_released_profit: float(subset.first().not_released_profit) + value,
        DbSubsetProfit.total_profit: float(subset.first().total_profit) + value
        })
    
    if commit:
        db.commit()
    
    return subset


def decrease_not_released_profit_by_user(user_id: int, value: float, db: Session, commit= True) :

    subset = db.query(DbSubsetProfit).filter(DbSubsetProfit.user_id == user_id )

    subset.update({DbSubsetProfit.not_released_profit: float(subset.first().not_released_profit) - value})
    
    if commit:
        db.commit()
    
    return subset


def increase_number_of_configs_by_user(user_id: int, db: Session, commit= True) :

    subset = db.query(DbSubsetProfit).filter(DbSubsetProfit.user_id == user_id )

    subset.update({DbSubsetProfit.number_of_configs: int(subset.first().number_of_configs) + 1})
    
    if commit:
        db.commit()
    
    return subset
