from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.data_models.db.user import User
from app.data_models.order_tracking import DateRangeSearchResponse, OrderTrackingDateRequest
from app.services.db_session import db_session
from app.services.order_history import OrderTrackingDate
from app.services.user_auth import get_current_user

router = APIRouter()


@router.post("/order_tracking_date", response_model=DateRangeSearchResponse, name="order_tracking_date")
async def get_order_by_date_full_history(
    request: OrderTrackingDateRequest,   #定义了数据发送的格式
    current_user: User = Depends(get_current_user),  #depends表示这个参数需要从get_current_user函数获取
    db: Session = Depends(db_session.get_db),
) -> DateRangeSearchResponse:
    
    start_date = request.start_date
    end_date = request.end_date
    order_tracking = OrderTrackingDate(
        user=current_user, 
        start_date=start_date, 
        end_date=end_date, 
        db_session=db
    )
    return order_tracking.build_order_date_full_history()
