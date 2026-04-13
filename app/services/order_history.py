from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional,Any
import pytz
from fastapi import HTTPException
from sqlalchemy import Numeric, cast, distinct, func
from sqlalchemy.orm import Session, joinedload

from app.data_models.db.container import Container
from app.data_models.db.vessel import Vessel
from app.data_models.db.order import Order
from app.data_models.db.pallet import Pallet
from app.data_models.db.shipment import Shipment
from app.data_models.db.user import User
from app.data_models.order_tracking import (
    OrderPostportResponse,
    OrderPreportResponse,
    OrderResponse,
    PalletShipmentSummary,
    ContainerFullResponse,
    ContainerBasicInfo,
    ContainerShipmentStatus,
    DestinationStatusGroup,
    DateRangeSearchResponse,
    ContainerDateResponse
)


class OrderTracking:
    #整合了柜号查询和日期查询
    def __init__(self, user: User, db_session: Session, *, 
                 container_number: Optional[str] = None, 
                 start_date: Optional[datetime] = None,
                 end_date: Optional[datetime] = None
                ) -> None:
        self.user: User = user
        self.db_session = db_session
        self.tz = pytz.timezone("Asia/Shanghai")
       
        if container_number and (start_date or end_date):
            raise ValueError("Cannot specify both container_number and date range")
        if not container_number and not (start_date and end_date):
            raise ValueError("Must specify either container_number or date range")
        self.container_number = container_number
        self.start_date = start_date
        self.end_date = end_date
        

    def build_order_full_history(self) -> OrderResponse:
        #查找港前数据
        order_data = self._search_preport_history(self.container_number)
        #处理港前数据
        preport = self._build_preport_history(order_data)
        
        #查找港后数据
        if preport is not None:
            raw_results = self._search_postport_history(self.container_number)
            postport = self._build_postport_history(raw_results) 
        else:
            postport = None
        return OrderResponse(
            preport_timenode=preport,
            postport_timenode=postport,
        )

    def _search_preport_history(self, container_number) -> Optional[Order]:
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
                Container.container_number == container_number,
            )
        )
        
        if self.user.username != "superuser":
            order_data = order_data.filter(User.zem_name == self.user.zem_name)
        return order_data.first()

    def _build_preport_history(self,order_data: Optional[Order]) -> Optional[OrderPreportResponse]:
        if not order_data:  #这里改成，如果查不到这个柜号的信息，就返回空，页面显示一下找不到
            return None
            raise HTTPException(
                status_code=404,
                detail=f"No matching order found for {self.container_number}",
            )
        order_data = OrderPreportResponse.model_validate(order_data).model_dump()
        #构建基础信息
        if 'container' in order_data:
            order_data.update({
                'container_number': order_data['container'].get('container_number'),
                'container_type': order_data['container'].get('container_type'),
                'weight_lbs': order_data['container'].get('weight_lbs')
            })
        
        if 'vessel' in order_data:
            order_data.update({
                'vessel_eta': order_data['vessel'].get('vessel_eta'),
                'origin_port': order_data['vessel'].get('origin_port'),
                'destination_port': order_data['vessel'].get('destination_port'),
                'shipping_line': order_data['vessel'].get('shipping_line'),
                'vessel_name': order_data['vessel'].get('vessel')
            })
        preport_history = []
        pod = None
        if order_data.get("created_at"):
            container_num = order_data.get("container", {}).get("container_number") if order_data.get("container") else None
            preport_history.append(
                {
                    "status": "ORDER_CREATED",
                    "description": f"创建订单: {container_num}",
                    "timestamp": self._convert_tz(order_data.get("created_at")),
                }
            )
        if order_data.get("add_to_t49"):
            pod = order_data.get("vessel", {}).get("destination_port") if order_data.get("vessel") else None
            if order_data["retrieval"].get("temp_t49_pod_arrive_at") and pod:
                preport_history.append(
                    {
                        "status": "ARRIVED_AT_PORT",
                        "description": f"到达港口: {pod}",
                        "location": pod,
                        "timestamp": self._convert_tz(
                            order_data["retrieval"]["temp_t49_pod_arrive_at"]
                        ),
                    }
                )
            if order_data["retrieval"].get("planned_release_time") and pod:
                preport_history.append(
                    {
                        "status": "PORT_UNLOADING",
                        "description": f"放行时间",
                        "location": pod,
                        "timestamp": self._convert_tz(
                            order_data["retrieval"]["planned_release_time"]
                        ),
                    }
                )
        if order_data["retrieval"]:
            if order_data["retrieval"].get("target_retrieval_timestamp_lower"):
                lower_time = order_data["retrieval"].get("target_retrieval_timestamp_lower")
                upper_time = order_data["retrieval"].get("target_retrieval_timestamp")
                if lower_time and upper_time:
                    time_range = f"{self._format_date_only(lower_time)} 到 {self._format_date_only(upper_time)}"
                elif upper_time:
                    time_range = self._format_date_only(upper_time)
                else:
                    time_range = ""
                preport_history.append(
                    {
                        "status": "PORT_PICKUP_SCHEDULED",
                        "description": f"预计提柜时间 {time_range}",                       
                        "location": pod,
                        "timestamp": order_data["retrieval"].get("target_retrieval_timestamp_lower"),
                    }
                )
            if order_data["retrieval"].get("actual_retrieval_timestamp"):
                preport_history.append(
                    {
                        "status": "ARRIVE_AT_WAREHOUSE",
                        "description": f"提柜完成",
                        "location": order_data["retrieval"].get("retrieval_destination_precise"),
                        "timestamp": order_data["retrieval"].get("actual_retrieval_timestamp"),
                    }
                )
        if order_data["offload"]:
            if order_data["offload"].get("offload_at"):
                retrieval_dest = order_data["retrieval"].get("retrieval_destination_precise") if order_data.get("retrieval") else None
                preport_history.append(
                    {
                        "status": "OFFLOAD",
                        "description": "拆柜完成",
                        "location": retrieval_dest,
                        "timestamp": self._convert_tz(
                            order_data["offload"].get("offload_at")
                        ),
                    }
                )
            if order_data["retrieval"] and order_data["retrieval"].get("empty_returned"):
                preport_history.append(
                    {
                        "status": "EMPTY_RETURN",
                        "description": f"已归还空箱",
                        "timestamp": self._convert_tz(
                            order_data["retrieval"]["empty_returned_at"]
                        ) if order_data["retrieval"].get("empty_returned_at") else None,
                    }
                )
        order_data["history"] = preport_history
        return OrderPreportResponse.model_validate(order_data)

    def _search_postport_history(self, container_number) -> List[Any]:
        try:
            return (
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
                    func.sum(Pallet.pcs).label("pcs"),
                )
                .join(Pallet.container)
                .outerjoin(Pallet.shipment)
                .filter(Container.container_number == container_number)
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
    
    def _build_postport_history(self, raw_results: List[Any]) -> OrderPostportResponse:       
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
            for row in raw_results
        ]
        return OrderPostportResponse(shipment=data)

    def _convert_tz(self, ts: datetime) -> datetime:
        if not ts:
            return ts
        else:
            return ts.astimezone(self.tz).replace(tzinfo=None)

    def _format_date_only(self, ts: datetime) -> str:
        if not ts:
            return ''
        return ts.strftime('%Y-%m-%d')


class BatchOrderTracking:
    def __init__(self, user: User, db_session: Session) -> None:
        self.user: User = user
        self.db_session = db_session
        self.tz = pytz.timezone("Asia/Shanghai")
    
    def build_all_orders(self, container_numbers: list) -> list[OrderResponse]:
        import traceback
        from datetime import datetime, timedelta
        
        try:
            six_months_ago = datetime.utcnow() - timedelta(days=180)
            
            print(f"BatchOrderTracking.build_all_orders called with {len(container_numbers)} containers")
            print(f"Current user: username={self.user.username}, zem_name={self.user.zem_name}, zem_code={getattr(self.user, 'zem_code', 'N/A')}")
            
            # 批量查询preport数据
            order_query = (
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
                    Container.container_number.in_(container_numbers),
                    Order.created_at >= six_months_ago
                )
            )
            
            if self.user.username != "superuser":
                order_query = order_query.filter(User.zem_name == self.user.zem_name)
            
            orders = order_query.all()
            print(f"Found {len(orders)} orders from database")
            
            if not orders:
                return []
            
            # 收集所有container_number
            found_container_numbers = []
            for order in orders:
                if order.container:
                    found_container_numbers.append(order.container.container_number)
                    if order.user:
                        print(f"Order {order.id}: container={order.container.container_number}, user.zem_code={order.user.zem_code}")
            
            print(f"Found {len(found_container_numbers)} container numbers")
            
            # 批量查询postport数据
            postport_results = (
                self.db_session.query(
                    Container.container_number,
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
                    func.round(cast(func.sum(Pallet.cbm), Numeric), 4).label("cbm"),
                    func.round(
                        cast(func.sum(Pallet.weight_lbs) / 2.20462, Numeric), 2
                    ).label("weight_kg"),
                    func.count(distinct(Pallet.id)).label("n_pallet"),
                    func.sum(Pallet.pcs).label("pcs"),
                )
                .select_from(Pallet)
                .join(Pallet.container)
                .outerjoin(Pallet.shipment)
                .filter(Container.container_number.in_(found_container_numbers))
                .group_by(
                    Container.container_number,
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
            print(f"Found {len(postport_results)} postport results")
            
            # 按container_number分组postport数据
            postport_by_container = {}
            for row in postport_results:
                cn = row[0]
                if cn not in postport_by_container:
                    postport_by_container[cn] = []
                postport_by_container[cn].append(row[1:])
            
            # 构建响应
            containers = []
            for order in orders:
                if not order.container:
                    continue
                
                # 构建preport
                preport = self._build_single_preport(order)
                if not preport:
                    continue
                
                # 构建postport
                cn = order.container.container_number
                postport_rows = postport_by_container.get(cn, [])
                postport = self._build_single_postport(postport_rows)
                
                containers.append(OrderResponse(
                    preport_timenode=preport,
                    postport_timenode=postport,
                ))
            
            print(f"Built {len(containers)} container responses")
            return containers
            
        except Exception as e:
            print(f"Error in BatchOrderTracking.build_all_orders: {str(e)}")
            print(traceback.format_exc())
            raise
    
    def _build_single_preport(self, order: Order) -> OrderPreportResponse:
        try:
            order_data = OrderPreportResponse.model_validate(order).model_dump()
        except Exception as e:
            container_num = order.container.container_number if order.container else 'N/A'
            user_info = f"user.zem_code={order.user.zem_code if order.user else 'N/A'}" if order.user else "user=None"
            raise Exception(f"Validation error for Order {order.id}, container={container_num}, {user_info}: {str(e)}")
        
        preport_history = []
        pod = None
        
        if order_data.get("created_at"):
            container_num = order_data.get("container", {}).get("container_number") if order_data.get("container") else None
            preport_history.append(
                {
                    "status": "ORDER_CREATED",
                    "description": f"创建订单: {container_num}",
                    "timestamp": self._convert_tz(order_data.get("created_at")),
                }
            )
        if order_data.get("add_to_t49"):
            pod = order_data.get("vessel", {}).get("destination_port") if order_data.get("vessel") else None
            if order_data["retrieval"] and order_data["retrieval"].get("temp_t49_pod_arrive_at") and pod:
                preport_history.append(
                    {
                        "status": "ARRIVED_AT_PORT",
                        "description": f"到达港口: {pod}",
                        "location": pod,
                        "timestamp": self._convert_tz(
                            order_data["retrieval"]["temp_t49_pod_arrive_at"]
                        ),
                    }
                )
            if order_data["retrieval"] and order_data["retrieval"].get("planned_release_time"):
                preport_history.append(
                    {
                        "status": "PORT_UNLOADING",
                        "description": f"放行时间",
                        "location": pod,
                        "timestamp": self._convert_tz(
                            order_data["retrieval"]["planned_release_time"]
                        ),
                    }
                )
        if order_data["retrieval"]:
            if order_data["retrieval"].get("target_retrieval_timestamp_lower"):
                lower_time = order_data["retrieval"].get("target_retrieval_timestamp_lower")
                upper_time = order_data["retrieval"].get("target_retrieval_timestamp")
                if lower_time and upper_time:
                    time_range = f"{self._format_date_only(lower_time)} 到 {self._format_date_only(upper_time)}"
                elif upper_time:
                    time_range = self._format_date_only(upper_time)
                else:
                    time_range = ""
                preport_history.append(
                    {
                        "status": "PORT_PICKUP_SCHEDULED",
                        "description": f"预计提柜时间 {time_range}",                       
                        "location": pod,
                        "timestamp": order_data["retrieval"].get("target_retrieval_timestamp_lower"),
                    }
                )
            if order_data["retrieval"].get("actual_retrieval_timestamp"):
                preport_history.append(
                    {
                        "status": "ARRIVE_AT_WAREHOUSE",
                        "description": f"提柜完成",
                        "location": order_data["retrieval"].get("retrieval_destination_precise"),
                        "timestamp": order_data["retrieval"].get("actual_retrieval_timestamp"),
                    }
                )
        if order_data["offload"]:
            if order_data["offload"].get("offload_at"):
                retrieval_dest = order_data["retrieval"].get("retrieval_destination_precise") if order_data.get("retrieval") else None
                preport_history.append(
                    {
                        "status": "OFFLOAD",
                        "description": "拆柜完成",
                        "location": retrieval_dest,
                        "timestamp": self._convert_tz(
                            order_data["offload"].get("offload_at")
                        ),
                    }
                )
            if order_data["retrieval"] and order_data["retrieval"].get("empty_returned"):
                preport_history.append(
                    {
                        "status": "EMPTY_RETURN",
                        "description": f"已归还空箱",
                        "timestamp": self._convert_tz(
                            order_data["retrieval"]["empty_returned_at"]
                        ) if order_data["retrieval"].get("empty_returned_at") else None,
                    }
                )
        order_data["history"] = preport_history
        return OrderPreportResponse.model_validate(order_data)
    
    def _build_single_postport(self, rows: list) -> OrderPostportResponse:
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
            for row in rows
        ]
        return OrderPostportResponse(shipment=data)
    
    def _convert_tz(self, ts: datetime) -> datetime:
        if not ts:
            return ts
        else:
            return ts.astimezone(self.tz).replace(tzinfo=None)

    def _format_date_only(self, ts: datetime) -> str:
        if not ts:
            return ''
        return ts.strftime('%Y-%m-%d')
