
"""
订单追踪服务模块

提供柜号查询的核心业务逻辑，包括：
1. 港前轨迹查询（订单创建到拆柜完成）
2. 港后轨迹查询（托盘运输状态）
3. 权限验证（客户只能查看自己的柜子）

【关键业务规则】
1. 客户登录：查询柜号时需验证该柜子是否归属此客户
   - 通过订单关联的 customer_name_id 判断归属
   - 非归属柜子返回 has_permission=False

2. 员工登录：查询柜号时无需验证归属，可查看所有柜子
"""
from datetime import datetime
from typing import Optional

import pytz
from fastapi import HTTPException
from sqlalchemy import Numeric, cast, distinct, func
from sqlalchemy.orm import Session, joinedload

from app.data_models.db.container import Container
from app.data_models.db.order import Order
from app.data_models.db.pallet import Pallet
from app.data_models.db.pallet_exception import PalletException
from app.data_models.db.packing_list import PackingList
from app.data_models.db.shipment import Shipment
from app.data_models.db.offload import Offload
from app.data_models.db.retrieval import Retrieval
from app.data_models.db.user import Customer, AuthUser
from app.data_models.wechat.order_tracking import (
    OrderPostportResponse,
    OrderPreportResponse,
    OrderResponse,
    PalletShipmentSummary,
)


class OrderTracking:
    """
    订单追踪服务类

    【功能说明】
    1. 根据柜号或唛头查询完整的物流追踪信息
    2. 根据用户类型进行权限验证
    3. 构建港前和港后的时间轴数据

    【查询逻辑】
    1. 先按柜号查询
    2. 若没查到，按唛头查询 pallet 表的 shipping_mark
    3. 若还没查到，再查 pallet 表的其他可能字段
    4. 找到对应柜号后，按原流程查询

    【权限验证逻辑】
    - 员工用户（is_staff=True）：直接返回完整信息
    - 客户用户（is_customer=True）：验证柜号归属后返回
    """

    def __init__(
        self,
        user: Customer | AuthUser,
        query: str,
        db_session: Session,
    ) -> None:
        """
        初始化订单追踪服务

        Args:
            user: 当前登录用户
            query: 要查询的内容（柜号或唛头）
            db_session: 数据库会话
        """
        self.user = user
        self.original_query = query
        self.container_number, self.matched_shipping_mark, self.is_mark_query = self._resolve_container_number(query, db_session)
        self.db_session = db_session
        self.tz = pytz.timezone("Asia/Shanghai")

    def _resolve_container_number(self, query: str, db_session: Session) -> tuple:
        """
        根据查询内容解析出柜号

        Args:
            query: 用户输入的查询内容
            db_session: 数据库会话

        Returns:
            tuple: (柜号, 匹配的shipping_mark, 是否是通过唛头查询到的)
        """
        # 第一步：先按柜号查询 Container 表
        container = db_session.query(Container).filter(
            Container.container_number == query
        ).first()
        if container:
            return container.container_number, None, False

        # 第二步：按唛头查询 PackingList 表的 shipping_mark
        packing_list = db_session.query(PackingList).options(
            joinedload(PackingList.container)
        ).filter(
            PackingList.shipping_mark == query
        ).first()
        if packing_list and packing_list.container:
            return packing_list.container.container_number, packing_list.shipping_mark, True

        # 第三步：按唛头模糊查询 PackingList 表的 shipping_mark
        packing_list = db_session.query(PackingList).options(
            joinedload(PackingList.container)
        ).filter(
            PackingList.shipping_mark.like(f"%{query}%")
        ).first()
        if packing_list and packing_list.container:
            return packing_list.container.container_number, packing_list.shipping_mark, True

        # 第四步：按唛头查询 Pallet 表的 shipping_mark
        pallet = db_session.query(Pallet).options(
            joinedload(Pallet.container)
        ).filter(
            Pallet.shipping_mark == query
        ).first()
        if pallet and pallet.container:
            return pallet.container.container_number, pallet.shipping_mark, True

        # 第五步：如果还没查到，尝试模糊查询 shipping_mark
        pallet = db_session.query(Pallet).options(
            joinedload(Pallet.container)
        ).filter(
            Pallet.shipping_mark.like(f"%{query}%")
        ).first()
        if pallet and pallet.container:
            return pallet.container.container_number, pallet.shipping_mark, True

        # 如果都没找到，返回原查询内容
        return query, None, False

    def build_order_full_history(self) -> OrderResponse:
        """
        构建完整的订单追踪历史

        【处理流程】
        1. 查询订单基本信息（港前数据）
        2. 验证用户权限（客户用户需验证归属）
        3. 如果有权限，继续构建港后数据
        4. 返回完整的追踪响应

        Returns:
            OrderResponse: 完整的订单追踪响应
        """
        try:
            preport, has_permission, order_owner = self._build_preport_history()

            if not has_permission:
                return OrderResponse(
                    preport_timenode=None,
                    postport_timenode=None,
                    has_permission=False,
                    message=f"您没有权限查看柜号 {self.container_number} 的详情，该柜子归属于其他客户",
                )

            if preport is None:
                return OrderResponse(
                    preport_timenode=None,
                    postport_timenode=None,
                    has_permission=True,
                    message=f"未找到柜号 {self.container_number} 的相关信息",
                )

            postport = self._build_postport_history()

            return OrderResponse(
                preport_timenode=preport,
                postport_timenode=postport,
                has_permission=True,
                message=None,
            )
        except Exception as e:
            # 捕获所有异常，返回友好提示+打印错误日志
            print(f"Order tracking error: {str(e)}")  # 输出到Azure日志
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=400,
                detail=f"查询柜号 {self.container_number} 失败：{str(e)}"
            )

    def _build_preport_history(self) -> tuple[Optional[OrderPreportResponse], bool, Optional[str]]:
        """
        构建港前轨迹数据，同时进行权限验证

        【权限验证逻辑】
        1. 查询柜号对应的订单
        2. 如果是客户用户，检查订单的 customer_name_id 是否匹配
        3. 员工用户直接通过验证

        Returns:
            tuple: (港前数据, 是否有权限, 订单所属客户名称)
        """
        order_data = (
            self.db_session.query(Order)
            .join(Order.container)
            .options(
                joinedload(Order.customer),
                joinedload(Order.container),
                joinedload(Order.warehouse),
                joinedload(Order.vessel),
                joinedload(Order.retrieval),
                joinedload(Order.offload),
            )
            .filter(Container.container_number == self.container_number)
            .first()
        )

        if not order_data:
            return None, True, None

        # 修复：空值判断（order_data.customer可能为None）
        order_owner_zem_name = order_data.customer.zem_name if (order_data.customer and hasattr(order_data.customer, 'zem_name')) else None

        is_staff = isinstance(self.user, AuthUser)

        is_authorized = (
            is_staff
            or (order_owner_zem_name and hasattr(self.user, 'zem_name') and self.user.zem_name == order_owner_zem_name)
        )

        if not is_authorized:
            return None, False, order_owner_zem_name

        order_dict = OrderPreportResponse.model_validate(order_data).model_dump()
        preport_history = []
        pod = None

        # 1. 订单创建事件（空值判断）
        if order_dict.get("created_at"):
            preport_history.append({
                "status": "ORDER_CREATED",
                "description": f"创建订单: {order_dict.get('container', {}).get('container_number', '未知柜号')}",
                "timestamp": self._format_date_only(order_dict["created_at"]),
            })

        # 2. 港口相关事件（修复：多层级空值判断）
        if order_dict.get("add_to_t49"):
            vessel = order_dict.get("vessel", {})
            pod = vessel.get("destination_port") if vessel else None

            retrieval = order_dict.get("retrieval", {})
            if retrieval and retrieval.get("temp_t49_pod_arrive_at"):
                preport_history.append({
                    "status": "ARRIVED_AT_PORT",
                    "description": f"到达港口: {pod or '未知港口'}",
                    "location": pod,
                    "timestamp": self._format_date_only(retrieval["temp_t49_pod_arrive_at"]),
                })

            if retrieval and retrieval.get("temp_t49_pod_discharge_at"):
                preport_history.append({
                    "status": "PORT_UNLOADING",
                    "description": "港口卸货",
                    "location": pod,
                    "timestamp": self._format_date_only(retrieval["temp_t49_pod_discharge_at"]),
                })

        # 3. 提柜相关事件（修复：空值判断）
        retrieval = order_dict.get("retrieval", {})
        if retrieval:
            if retrieval.get("target_retrieval_timestamp_lower"):
                lower_time = retrieval.get("target_retrieval_timestamp_lower")
                upper_time = retrieval.get("target_retrieval_timestamp")
                if lower_time and upper_time:
                    time_range = f"{self._format_date_only(lower_time)} 到 {self._format_date_only(upper_time)}"
                elif upper_time:
                    time_range = self._format_date_only(upper_time)
                else:
                    time_range = ""
                preport_history.append({
                    "status": "PORT_PICKUP_SCHEDULED",
                    "description": f"预计提柜时间 {time_range}",
                    "location": pod,
                    "timestamp": self._format_date_only(retrieval["target_retrieval_timestamp_lower"]),
                })

            if retrieval.get("actual_retrieval_timestamp"):
                location = retrieval.get("retrieval_destination_precise")
                preport_history.append({
                    "status": "ARRIVE_AT_WAREHOUSE",
                    "description": "提柜完成",
                    "location": location,
                    "timestamp": self._format_date_only(retrieval.get("actual_retrieval_timestamp")),
                })

        # 4. 卸货/拆柜事件（修复：空值判断）
        offload = order_dict.get("offload", {})
        retrieval = order_dict.get("retrieval", {})
        if offload:
            if offload.get("offload_at"):
                location = retrieval.get("retrieval_destination_precise") if retrieval else None
                preport_history.append({
                    "status": "OFFLOAD",
                    "description": "拆柜完成",
                    "location": location,
                    "timestamp": self._format_date_only(offload["offload_at"]),
                })

            if retrieval and retrieval.get("empty_returned"):
                preport_history.append({
                    "status": "EMPTY_RETURN",
                    "description": "已归还空箱",
                    "timestamp": self._format_date_only(retrieval.get("empty_returned_at")),
                })

        order_dict["history"] = preport_history
        return OrderPreportResponse.model_validate(order_dict), True, order_owner_zem_name

    def _build_postport_history(self) -> OrderPostportResponse:
        try:
            pallet_query = (
                self.db_session.query(
                    Pallet.destination,
                    Pallet.PO_ID,
                    Pallet.delivery_method,
                    Pallet.note,
                    Pallet.delivery_type,
                    Shipment.shipment_batch_number,
                    Shipment.is_shipment_schduled,
                    Shipment.shipment_schduled_at,
                    Shipment.shipment_appointment.label("shipment_appointment"),
                    Shipment.is_shipped,
                    Shipment.shipped_at_utc.label("shipped_at"),
                    Shipment.is_arrived,
                    Shipment.arrived_at_utc.label("arrived_at"),
                    Shipment.pod_link,
                    Shipment.pod_uploaded_at,
                    Shipment.shipping_order_link,
                    Shipment.appointment_id,
                    Shipment.shipment_type,
                    PalletException.exception_type,
                    PalletException.exception_reason,
                    func.round(cast(func.sum(Pallet.cbm), Numeric), 4).label("cbm"),
                    func.round(
                        cast(func.sum(Pallet.weight_lbs) / 2.20462, Numeric), 2
                    ).label("weight_kg"),
                    func.count(distinct(Pallet.id)).label("n_pallet"),
                    func.sum(Pallet.pcs).label("pcs"),
                )
                .join(Pallet.container)
                .outerjoin(Pallet.shipment)
                .outerjoin(Pallet.exceptions)
                .filter(Container.container_number == self.container_number)
            )

            if self.is_mark_query and self.matched_shipping_mark:
                pallet_query = pallet_query.filter(Pallet.shipping_mark == self.matched_shipping_mark)

            pallet_query = pallet_query.group_by(
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
                Shipment.shipped_at_utc,
                Shipment.is_arrived,
                Shipment.arrived_at_utc,
                Shipment.pod_link,
                Shipment.pod_uploaded_at,
                Shipment.shipping_order_link,
                Shipment.appointment_id,
                Shipment.shipment_type,
                PalletException.exception_type,
                PalletException.exception_reason,
            )

            pallet_results = pallet_query.all()

            pallet_delivery_types = set()
            for row in pallet_results:
                if row[4]:
                    pallet_delivery_types.add(row[4])

            missing_delivery_types = set()
            for dt in ["public", "other"]:
                if dt not in pallet_delivery_types:
                    missing_delivery_types.add(dt)

            packing_list_results = []
            if missing_delivery_types:
                pl_query = (
                    self.db_session.query(
                        PackingList.destination,
                        PackingList.PO_ID,
                        PackingList.delivery_method,
                        PackingList.note,
                        PackingList.delivery_type,
                        Shipment.shipment_batch_number,
                        Shipment.is_shipment_schduled,
                        Shipment.shipment_schduled_at,
                        Shipment.shipment_appointment.label("shipment_appointment"),
                        Shipment.is_shipped,
                        Shipment.shipped_at_utc.label("shipped_at"),
                        Shipment.is_arrived,
                        Shipment.arrived_at_utc.label("arrived_at"),
                        Shipment.pod_link,
                        Shipment.pod_uploaded_at,
                        Shipment.shipping_order_link,
                        Shipment.appointment_id,
                        Shipment.shipment_type,
                        func.round(cast(func.sum(PackingList.cbm), Numeric), 4).label("cbm"),
                        func.round(
                            cast(func.sum(PackingList.total_weight_kg), Numeric), 2
                        ).label("weight_kg"),
                        func.sum(PackingList.n_pallet).label("n_pallet"),
                        func.sum(PackingList.pcs).label("pcs"),
                    )
                    .join(PackingList.container)
                    .outerjoin(PackingList.shipment)
                    .filter(Container.container_number == self.container_number)
                    .filter(PackingList.delivery_type.in_(missing_delivery_types))
                )

                if self.is_mark_query and self.matched_shipping_mark:
                    pl_query = pl_query.filter(PackingList.shipping_mark == self.matched_shipping_mark)

                pl_query = pl_query.group_by(
                    PackingList.destination,
                    PackingList.PO_ID,
                    PackingList.delivery_method,
                    PackingList.note,
                    PackingList.delivery_type,
                    Shipment.shipment_batch_number,
                    Shipment.is_shipment_schduled,
                    Shipment.shipment_schduled_at,
                    Shipment.shipment_appointment,
                    Shipment.is_shipped,
                    Shipment.shipped_at_utc,
                    Shipment.is_arrived,
                    Shipment.arrived_at_utc,
                    Shipment.pod_link,
                    Shipment.pod_uploaded_at,
                    Shipment.shipping_order_link,
                    Shipment.appointment_id,
                    Shipment.shipment_type,
                )

                packing_list_results = pl_query.all()

        except Exception as e:
            print(f"Postport query error: {str(e)}")
            import traceback
            traceback.print_exc()
            return OrderPostportResponse(shipment=[])

        data = []
        for row in pallet_results:
            data.append(
                PalletShipmentSummary(
                    destination=row[0],
                    PO_ID=row[1],
                    delivery_method=row[2],
                    note=row[3],
                    delivery_type=row[4],
                    master_shipment_batch_number=row[5],
                    is_shipment_schduled=row[6],
                    shipment_schduled_at=row[7],
                    shipment_appointment=row[8],
                    is_shipped=row[9],
                    shipped_at=row[10],
                    is_arrived=row[11],
                    arrived_at=row[12],
                    pod_link=row[13],
                    pod_uploaded_at=row[14],
                    shipping_order_link=row[15],
                    appointment_id=row[16],
                    shipment_type=row[17],
                    exception_type=row[18],
                    exception_reason=row[19],
                    cbm=row[20],
                    weight_kg=row[21],
                    n_pallet=row[22],
                    pcs=row[23],
                )
            )

        for row in packing_list_results:
            data.append(
                PalletShipmentSummary(
                    destination=row[0],
                    PO_ID=row[1],
                    delivery_method=row[2],
                    note=row[3],
                    delivery_type=row[4],
                    master_shipment_batch_number=row[5],
                    is_shipment_schduled=row[6],
                    shipment_schduled_at=row[7],
                    shipment_appointment=row[8],
                    is_shipped=row[9],
                    shipped_at=row[10],
                    is_arrived=row[11],
                    arrived_at=row[12],
                    pod_link=row[13],
                    pod_uploaded_at=row[14],
                    shipping_order_link=row[15],
                    appointment_id=row[16],
                    shipment_type=row[17],
                    exception_type=None,
                    exception_reason=None,
                    cbm=row[18],
                    weight_kg=row[19],
                    n_pallet=row[20],
                    pcs=row[21],
                )
            )

        return OrderPostportResponse(shipment=data)

    def _convert_tz(self, ts: datetime) -> Optional[datetime]:
        """
        将 UTC 时间转换为上海时区

        Args:
            ts: UTC 时间戳

        Returns:
            转换后的时间（不带时区信息）
        """
        if not ts:
            return None
        try:
            # 如果ts没有tzinfo，先添加UTC时区
            if ts.tzinfo is None:
                ts = pytz.UTC.localize(ts)
            return ts.astimezone(self.tz).replace(tzinfo=None)
        except Exception as e:
            print(f"Timezone convert error: {str(e)}")
            return ts  # 转换失败时返回原时间

    def _format_date_only(self, ts: datetime) -> str:
        """
        格式化日期（仅显示日期，不显示时间）

        Args:
            ts: 时间戳

        Returns:
            格式化后的日期字符串
        """
        if not ts:
            return ""
        try:
            return ts.strftime("%Y-%m-%d")
        except Exception as e:
            print(f"Date format error: {str(e)}")
            return ""

