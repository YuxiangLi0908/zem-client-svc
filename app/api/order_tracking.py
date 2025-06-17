from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.data_models.db.user import User
from app.data_models.order_tracking import OrderResponse, OrderTrackingRequest
from app.services.db_session import db_session
from app.services.order_history import OrderTracking
from app.services.user_auth import get_current_user

router = APIRouter()


@router.post("/order_tracking", response_model=OrderResponse, name="order_tracking")
async def get_order_full_history(
    request: OrderTrackingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> OrderResponse:
    container_number = request.container_number.strip()
    order_tracking = OrderTracking(
        user=current_user, container_number=container_number, db_session=db
    )
    return order_tracking.build_order_full_history()
