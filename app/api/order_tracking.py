from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.data_models.db.container import Container
from app.data_models.db.order import Order
from app.data_models.db.user import User
from app.data_models.order_tracking import OrderResponse, OrderTrackingRequest
from app.services.db_session import db_session
from app.services.user_auth import get_current_user

router = APIRouter()


@router.post("/order_tracking", response_model=OrderResponse, name="order_tracking")
def get_order_history(
    request: OrderTrackingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> OrderResponse:
    container_number = request.container_number
    order = (
        db.query(Order)
        .options(
            joinedload(Order.user),
            joinedload(Order.container),
            joinedload(Order.warehouse),
            joinedload(Order.vessel),
            joinedload(Order.retrieval),
            joinedload(Order.offload),
        )
        .filter(
            Container.container_number == container_number,
            User.zem_name == current_user.zem_name,
        )
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404, detail=f"No matching orders found for {container_number}"
        )

    return order
