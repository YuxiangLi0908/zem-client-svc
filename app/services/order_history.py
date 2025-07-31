from datetime import datetime

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
        self.tz = pytz.timezone("Asia/Shanghai")

    def build_order_full_history(self) -> OrderResponse:
        preport = self._build_preport_history()
        postport = self._build_postport_history() if preport is not None else None
        return OrderResponse(
            preport_timenode=preport,
            postport_timenode=postport,
        )

    def _build_preport_history(self) -> OrderPreportResponse:
        order_data = (
            self.db_session.query(Order)
            .join(Order.container)
            .join(Order.user)
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
            )
        )
        if self.user.username != "superuser":
            order_data = order_data.filter(User.zem_name == self.user.zem_name)
        order_data = order_data.first()
        if not order_data:  #这里改成，如果查不到这个柜号的信息，就返回空，页面显示一下找不到
            return None
            raise HTTPException(
                status_code=404,
                detail=f"No matching order found for {self.container_number}",
            )

        order_data = OrderPreportResponse.model_validate(order_data).model_dump()
        preport_history = []
        pod = None
        if order_data["created_at"]:
            preport_history.append(
                {
                    "status": "ORDER_CREATED",
                    "description": f"创建订单: {order_data['container']['container_number']}",
                    "timestamp": self._convert_tz(order_data["created_at"]),
                }
            )
        if order_data["add_to_t49"]:
            pod = order_data["vessel"]["destination_port"]
            if order_data["retrieval"]["temp_t49_pod_arrive_at"]:
                preport_history.append(
                    {
                        "status": "ARRIVED_AT_PORT",
                        "description": f"到达港口: {order_data['vessel']['destination_port']}",
                        "location": order_data["vessel"]["destination_port"],
                        "timestamp": self._convert_tz(
                            order_data["retrieval"]["temp_t49_pod_arrive_at"]
                        ),
                    }
                )
            if order_data["retrieval"]["temp_t49_pod_discharge_at"]:
                preport_history.append(
                    {
                        "status": "PORT_UNLOADING",
                        "description": f"港口卸货",
                        "location": order_data["vessel"]["destination_port"],
                        "timestamp": self._convert_tz(
                            order_data["retrieval"]["temp_t49_pod_discharge_at"]
                        ),
                    }
                )
        if order_data["retrieval"]:
            if order_data["retrieval"]["scheduled_at"]:
                preport_history.append(
                    {
                        "status": "PORT_PICKUP_SCHEDULED",
                        "description": f"预约港口提柜: 预计提柜时间 {self._convert_tz(order_data['retrieval']['target_retrieval_timestamp'])}",                       
                        "location": pod,
                        "timestamp": self._convert_tz(
                            order_data["retrieval"]["scheduled_at"]
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
                        "timestamp": self._convert_tz(
                            order_data["retrieval"]["arrive_at"]
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
                        "timestamp": self._convert_tz(
                            order_data["offload"]["offload_at"]
                        ),
                    }
                )
            if order_data["retrieval"]["empty_returned"]:
                preport_history.append(
                    {
                        "status": "EMPTY_RETURN",
                        "description": f"已归还空箱",
                        "timestamp": self._convert_tz(
                            order_data["retrieval"]["empty_returned_at"]
                        ),
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
                    Shipment.shipment_appointment_utc.label("shipment_appointment"),
                    Shipment.is_shipped,
                    Shipment.shipped_at_utc.label("shipped_at"),
                    Shipment.is_arrived,
                    Shipment.arrived_at_utc.label("arrived_at"),
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
                    Shipment.shipment_appointment_utc,
                    Shipment.is_shipped,
                    Shipment.shipped_at_utc,
                    Shipment.is_arrived,
                    Shipment.arrived_at_utc,
                    Shipment.pod_link,
                    Shipment.pod_uploaded_at,
                )
                .all()
            )
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"{e}: No shipment history for {self.container_number}",
            )
        data = [
            PalletShipmentSummary(
                destination=row[0],
                PO_ID=row[1],
                delivery_method=row[2],
                note=row[3],
                delivery_type=row[4],
                master_shipment_batch_number=row[5],
                is_shipment_schduled=row[6],
                shipment_schduled_at=self._convert_tz(row[7]),
                shipment_appointment=self._convert_tz(row[8]),
                is_shipped=row[9],
                shipped_at=self._convert_tz(row[10]),
                is_arrived=row[11],
                arrived_at=self._convert_tz(row[12]),
                pod_link=row[13],
                pod_uploaded_at=self._convert_tz(row[14]),
                cbm=row[15],
                weight_kg=row[16],
                n_pallet=row[17],
                pcs=row[18],
            )
            for row in results
        ]
        #print('查找数据',data)
        return OrderPostportResponse(shipment=data)

    def _convert_tz(self, ts: datetime) -> datetime:
        if not ts:
            return ts
        else:
            return ts.astimezone(self.tz).replace(tzinfo=None)
