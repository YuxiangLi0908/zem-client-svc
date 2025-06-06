
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.data_models.db.container import Container
from app.data_models.db.order import Order
from app.data_models.db.user import User
from app.data_models.order_tracking import OrderPreportResponse, OrderResponse, OrderPostportResponse


class OrderTracking:
    def __init__(self, user: str, container_number: str, db_session: Session) -> None:
        self.user: User = user
        self.container_number = container_number
        self.db_session = db_session

    def build_order_full_history(self) -> OrderResponse:
        return OrderResponse(
            preport_timenode=self._build_preport_history(),
            postport_timenode=self._build_postport_history(),
        )

    def _build_preport_history(self) -> OrderPreportResponse:
        preport_hist = (
            self.db_session.query(Order)
            .options(
                joinedload(Order.user),
                joinedload(Order.container),
                joinedload(Order.warehouse),
                joinedload(Order.vessel),
                joinedload(Order.retrieval),
                joinedload(Order.offload),
            )
            .filter(
                Container.container_number == self.container_number,
                User.zem_name == self.user.zem_name,
            )
            .first()
        )

        if not preport_hist:
            raise HTTPException(
                status_code=404, detail=f"No matching order found for {self.container_number}"
            )
        return OrderPreportResponse.model_validate(preport_hist)
    
    def _build_postport_history(self) -> OrderPostportResponse:
        # TODO
        return OrderPostportResponse(order_id="test-order-id")
