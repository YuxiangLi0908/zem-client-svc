import pytz
from fastapi import HTTPException
from sqlalchemy import Numeric, cast, distinct, func
from sqlalchemy.orm import Session, joinedload

from app.data_models.db.container import Container
from app.data_models.db.order import Order
from app.data_models.db.pallet import Pallet
from app.data_models.db.shipment import Shipment
from app.data_models.db.user import User
from app.data_models.order_tracking import (
    OrderPostportResponse,
    OrderPreportResponse,
    OrderResponse,
    PalletShipmentSummary,
)


class OrderTracking:
    def __init__(self, user: User, container_number: str, db_session: Session) -> None:
        self.user: User = user
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
            .join(Order.container)
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

        if not order_data:
            raise HTTPException(
                status_code=404,
                detail=f"No matching order found for {self.container_number}",
            )

        order_data = OrderPreportResponse.model_validate(order_data).model_dump()
        preport_history = []
        china_tz = pytz.timezone("Asia/Shanghai")
        pod = None
        if order_data["created_at"]:
            preport_history.append(
                {
                    "status": "ORDER_CREATED",
                    "description": f"创建订单: {order_data['container']['container_number']}",
                    "timestamp": order_data["created_at"].astimezone(china_tz),
                }
            )
        if order_data["add_to_t49"]:
            pod = order_data["vessel"]["destination_port"]
            if order_data["retrieval"]["temp_t49_pod_arrive_at"]:
                preport_history.append(
                    {
                        "status": "IN_TRANSIT",
                        "description": f"到达港口: {order_data['vessel']['destination_port']}",
                        "location": order_data["vessel"]["destination_port"],
                        "timestamp": order_data["retrieval"][
                            "temp_t49_pod_arrive_at"
                        ].astimezone(china_tz),
                    }
                )
            if order_data["retrieval"]["temp_t49_pod_discharge_at"]:
                preport_history.append(
                    {
                        "status": "IN_TRANSIT",
                        "description": f"港口卸货",
                        "location": order_data["vessel"]["destination_port"],
                        "timestamp": order_data["retrieval"][
                            "temp_t49_pod_discharge_at"
                        ].astimezone(china_tz),
                    }
                )
        if order_data["retrieval"]:
            if order_data["retrieval"]["scheduled_at"]:
                preport_history.append(
                    {
                        "status": "IN_TRANSIT",
                        "description": f"预约港口提柜: 预计提柜时间 {order_data['retrieval']['target_retrieval_timestamp'].astimezone(china_tz)}",
                        "location": pod,
                        "timestamp": order_data["retrieval"]["scheduled_at"].astimezone(
                            china_tz
                        ),
                    }
                )
            if order_data["retrieval"]["arrive_at_destination"]:
                preport_history.append(
                    {
                        "status": "ARRIVE_AT_WAREHOUSE",
                        "description": f"港口提柜完成, 货柜到达目的仓点 {order_data['retrieval']['retrieval_destination_precise']}",
                        "location": order_data["retrieval"][
                            "retrieval_destination_precise"
                        ],
                        "timestamp": order_data["retrieval"]["arrive_at"].astimezone(
                            china_tz
                        ),
                    }
                )
        if order_data["offload"]:
            if order_data["offload"]["offload_at"]:
                preport_history.append(
                    {
                        "status": "OFFLOAD",
                        "description": "拆柜完成",
                        "location": order_data["retrieval"][
                            "retrieval_destination_precise"
                        ],
                        "timestamp": order_data["offload"]["offload_at"].astimezone(
                            china_tz
                        ),
                    }
                )
            if order_data["retrieval"]["empty_returned"]:
                preport_history.append(
                    {
                        "status": "EMPTY_RETURN",
                        "description": f"已归还空箱",
                        "timestamp": order_data["retrieval"][
                            "empty_returned_at"
                        ].astimezone(china_tz),
                    }
                )
        order_data["history"] = preport_history
        return OrderPreportResponse.model_validate(order_data)

    def _build_postport_history(self) -> OrderPostportResponse:
        try:
            results = (
                self.db_session.query(
                    Pallet.destination,
                    Pallet.PO_ID,
                    Pallet.delivery_method,
                    Pallet.note,
                    Pallet.delivery_type,
                    Shipment.shipment_batch_number,
                    Shipment.is_shipment_schduled,
                    Shipment.shipment_schduled_at,
                    Shipment.shipment_appointment,
                    Shipment.is_shipped,
                    Shipment.shipped_at,
                    Shipment.is_arrived,
                    Shipment.arrived_at,
                    Shipment.pod_link,
                    Shipment.pod_uploaded_at,
                    func.round(cast(func.sum(Pallet.cbm), Numeric), 4).label("cbm"),
                    func.round(
                        cast(func.sum(Pallet.weight_lbs) / 2.20462, Numeric), 2
                    ).label("weight_kg"),
                    func.count(distinct(Pallet.id)).label("n_pallet"),
                    func.count(Pallet.pcs).label("pcs"),
                )
                .join(Pallet.container)
                .outerjoin(Pallet.shipment)
                .filter(Container.container_number == self.container_number)
                .group_by(
                    Pallet.destination,
                    Pallet.PO_ID,
                    Pallet.delivery_method,
                    Pallet.note,
                    Pallet.delivery_type,
                    Shipment.shipment_batch_number,
                    Shipment.is_shipment_schduled,
                    Shipment.shipment_schduled_at,
                    Shipment.shipment_appointment,
                    Shipment.is_shipped,
                    Shipment.shipped_at,
                    Shipment.is_arrived,
                    Shipment.arrived_at,
                    Shipment.pod_link,
                    Shipment.pod_uploaded_at,
                )
                .all()
            )
        except:
            raise HTTPException(
                status_code=404,
                detail=f"No shipment history for {self.container_number}",
            )
        data = [
            PalletShipmentSummary(
                destination=row[0],
                PO_ID=row[1],
                delivery_method=row[2],
                note=row[3],
                delivery_type=row[4],
                shipment_batch_number=row[5],
                is_shipment_schduled=row[6],
                shipment_schduled_at=row[7],
                shipment_appointment=row[8],
                is_shipped=row[9],
                shipped_at=row[10],
                is_arrived=row[11],
                arrived_at=row[12],
                pod_link=row[13],
                pod_uploaded_at=row[14],
                cbm=row[15],
                weight_kg=row[16],
                n_pallet=row[17],
                pcs=row[18],
            )
            for row in results
        ]
        return OrderPostportResponse(shipment=data)
