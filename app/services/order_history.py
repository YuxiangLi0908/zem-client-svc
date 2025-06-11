
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.data_models.db.container import Container
from app.data_models.db.order import Order
from app.data_models.db.user import User
from app.data_models.order_tracking import OrderPreportResponse, OrderResponse, OrderPostportResponse


class OrderTracking:
    def __init__(self, user: str, container_number: str, db_session: Session) -> None:
        # self.user: User = user
        self.container_number = container_number
        self.db_session = db_session

    def build_order_full_history(self) -> OrderResponse:
        return OrderResponse(
            preport_timenode=self._build_preport_history(),
            postport_timenode=self._build_postport_history(),
        )

    def _build_preport_history(self) -> OrderPreportResponse:
        order_data = (
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
                # User.zem_name == self.user.zem_name,
            )
            .first()
        )

        if not order_data:
            raise HTTPException(
                status_code=404, detail=f"No matching order found for {self.container_number}"
            )
        
        order_data = OrderPreportResponse.model_validate(order_data).model_dump()
        preport_history = []
        if order_data["created_at"]:
            preport_history.append({
                "status": "ORDER_CREATED",
                "description": f"创建订单: {order_data['container']['container_number']}",
                "timestamp": order_data["created_at"],
            })
        if order_data["add_to_t49"]:
            if order_data["retrieval"]["temp_t49_pod_arrive_at"]:
                preport_history.append({
                    "status": "IN_TRANSIT",
                    "description": f"到达港口: {order_data['vessel']['destination_port']}",
                    "location": order_data["vessel"]["destination_port"],
                    "timestamp": order_data["retrieval"]["temp_t49_pod_arrive_at"],
                })
            if order_data["retrieval"]["temp_t49_pod_discharge_at"]:
                preport_history.append({
                    "status": "IN_TRANSIT",
                    "description": f"港口卸货",
                    "location": order_data["vessel"]["destination_port"],
                    "timestamp": order_data["retrieval"]["temp_t49_pod_discharge_at"],
                })
        if order_data["retrieval"]:
            if order_data["retrieval"]["scheduled_at"]:
                preport_history.append({
                    "status": "IN_TRANSIT",
                    "description": f"预约港口提柜: 预计提柜时间 {order_data['retrieval']['target_retrieval_timestamp']}",
                    "location": order_data["vessel"]["destination_port"],
                    "timestamp": order_data["retrieval"]["scheduled_at"],
                })
            if order_data["retrieval"]["arrive_at_destination"]:
                preport_history.append({
                    "status": "ARRIVE_AT_WAREHOUSE",
                    "description": f"港口提柜完成, 货柜到达目的仓点 {order_data['retrieval']['retrieval_destination_precise']}",
                    "location": order_data["retrieval"]["retrieval_destination_precise"],
                    "timestamp": order_data["retrieval"]["arrive_at"],
                })
        if order_data["offload"]:
            if order_data["offload"]["offload_at"]:
                preport_history.append({
                    "status": "OFFLOAD",
                    "description": "拆柜完成",
                    "location": order_data["retrieval"]["retrieval_destination_precise"],
                    "timestamp": order_data["offload"]["offload_at"],
                })
            if order_data["retrieval"]["empty_returned"]:
                preport_history.append({
                    "status": "EMPTY_RETURN",
                    "description": f"已归还空箱",
                    "timestamp": order_data["retrieval"]["empty_returned_at"],
                })

        order_data["history"] = preport_history
        return OrderPreportResponse.model_validate(order_data)
    
    def _build_postport_history(self) -> OrderPostportResponse:
        # TODO
        return OrderPostportResponse(order_id="test-order-id")
