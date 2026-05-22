
"""
表查询服务模块

提供表查询的核心业务逻辑：
1. 只有特定用户（sangwei, yuxiang.li, qyj）可以使用
2. 可以选择查询哪个表
3. 可以通过 ID 或柜号查询
4. 返回查询到的所有记录
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from app.data_models.db.user import User
from app.data_models.wechat.order_tracking import TableQueryResponse


class TableQuery:
    """
    表查询服务类
    """

    # 白名单用户
    AUTHORIZED_USERS = {"sangwei", "yuxiang.li", "qyj"}

    def __init__(self, user: User, db_session: Session) -> None:
        self.user = user
        self.db_session = db_session

    def _is_authorized(self) -> bool:
        """检查用户是否有权限"""
        return self.user.username in self.AUTHORIZED_USERS

    def _get_available_tables(self) -> List[Dict]:
        """获取可用的表列表"""
        # 动态导入所有db模型
        from app.data_models.db import (
            container, order, pallet, packing_list, shipment,
            retrieval, offload, vessel, warehouse, user,
            pallet_exception, fee_detail, quotation_master,
            fleet, maersk_price_rate,
        )

        tables = []
        model_map = {
            "Container": container.Container,
            "Order": order.Order,
            "Pallet": pallet.Pallet,
            "PackingList": packing_list.PackingList,
            "Shipment": shipment.Shipment,
            "Retrieval": retrieval.Retrieval,
            "Offload": offload.Offload,
            "Vessel": vessel.Vessel,
            "Warehouse": warehouse.Warehouse,
            "User": user.User,
            "PalletException": pallet_exception.PalletException,
            "FeeDetail": fee_detail.FeeDetail,
            "QuotationMaster": quotation_master.QuotationMaster,
            "Fleet": fleet.Fleet,
            "MaerskPriceRate": maersk_price_rate.MaerskPriceRate,
        }

        for table_name, model in model_map.items():
            tables.append({
                "name": table_name,
                "description": model.__tablename__ if hasattr(model, "__tablename__") else table_name,
            })

        return tables

    def _get_model_by_name(self, table_name: str) -> Optional[type]:
        """根据表名获取模型类"""
        from app.data_models.db import (
            container, order, pallet, packing_list, shipment,
            retrieval, offload, vessel, warehouse, user,
            pallet_exception, fee_detail, quotation_master,
            fleet, maersk_price_rate,
        )

        model_map = {
            "Container": container.Container,
            "Order": order.Order,
            "Pallet": pallet.Pallet,
            "PackingList": packing_list.PackingList,
            "Shipment": shipment.Shipment,
            "Retrieval": retrieval.Retrieval,
            "Offload": offload.Offload,
            "Vessel": vessel.Vessel,
            "Warehouse": warehouse.Warehouse,
            "User": user.User,
            "PalletException": pallet_exception.PalletException,
            "FeeDetail": fee_detail.FeeDetail,
            "QuotationMaster": quotation_master.QuotationMaster,
            "Fleet": fleet.Fleet,
            "MaerskPriceRate": maersk_price_rate.MaerskPriceRate,
        }

        return model_map.get(table_name)

    def _get_available_fields(self, model) -> List[Dict]:
        """获取模型的可用字段"""
        if not model:
            return []

        fields = []
        mapper = inspect(model)

        # 添加ID字段
        fields.append({
            "name": "id",
            "type": "integer",
            "is_key": True,
        })

        # 添加柜号字段（如果有关联）
        # 先检查是否有container_number_id字段
        if hasattr(model, "container_number_id"):
            fields.append({
                "name": "container_number",
                "type": "string",
                "is_key": False,
                "is_related": True,
                "related_field": "container_number_id",
            })

        # 检查是否有shipping_mark字段
        if hasattr(model, "shipping_mark"):
            fields.append({
                "name": "shipping_mark",
                "type": "string",
                "is_key": False,
            })

        return fields

    def _convert_record_to_dict(self, record) -> Dict:
        """将记录转换为字典"""
        if not record:
            return {}

        result = {}
        mapper = inspect(type(record))

        for column in mapper.columns:
            value = getattr(record, column.key)
            # 处理 datetime 和其他特殊类型
            if hasattr(value, "isoformat"):
                result[column.key] = value.isoformat()
            elif isinstance(value, (int, float, str, bool, type(None))):
                result[column.key] = value
            else:
                result[column.key] = str(value)

        return result

    def query_table(self, table_name: str, search_field: str, search_value: str) -> TableQueryResponse:
        """
        查询表数据

        Args:
            table_name: 表名
            search_field: 查询字段（id 或 container_number）
            search_value: 查询值

        Returns:
            TableQueryResponse: 查询结果
        """
        # 1. 权限检查
        if not self._is_authorized():
            return TableQueryResponse(
                has_permission=False,
                message="您没有权限使用表查询功能",
                records=[],
                record_count=0,
                available_fields=[],
                tables=self._get_available_tables(),
            )

        # 2. 获取模型
        model = self._get_model_by_name(table_name)
        if not model:
            return TableQueryResponse(
                has_permission=True,
                message=f"未找到表 {table_name}",
                records=[],
                record_count=0,
                available_fields=[],
                tables=self._get_available_tables(),
            )

        # 3. 构建查询
        from app.data_models.db.container import Container

        query = self.db_session.query(model)
        records = []

        try:
            if search_field == "id":
                # 按ID查询
                try:
                    record_id = int(search_value)
                    record = query.filter(model.id == record_id).first()
                    if record:
                        records.append(record)
                except ValueError:
                    return TableQueryResponse(
                        has_permission=True,
                        message=f"ID值必须是整数: {search_value}",
                        records=[],
                        record_count=0,
                        available_fields=self._get_available_fields(model),
                        tables=self._get_available_tables(),
                    )

            elif search_field == "container_number":
                # 按柜号查询（需要先查Container表）
                # 先检查模型是否有container_number_id字段
                if hasattr(model, "container_number_id"):
                    # 先查Container表找到对应的ID
                    container_record = self.db_session.query(Container).filter(
                        Container.container_number == search_value
                    ).first()

                    if container_record:
                        # 使用找到的ID查询
                        records = query.filter(
                            model.container_number_id == container_record.id
                        ).all()
                    else:
                        return TableQueryResponse(
                            has_permission=True,
                            message=f"未找到柜号 {search_value}",
                            records=[],
                            record_count=0,
                            available_fields=self._get_available_fields(model),
                            tables=self._get_available_tables(),
                        )
                else:
                    return TableQueryResponse(
                        has_permission=True,
                        message=f"表 {table_name} 不支持按柜号查询",
                        records=[],
                        record_count=0,
                        available_fields=self._get_available_fields(model),
                        tables=self._get_available_tables(),
                    )

            elif search_field == "shipping_mark":
                # 按唛头查询
                if hasattr(model, "shipping_mark"):
                    records = query.filter(model.shipping_mark == search_value).all()
                else:
                    return TableQueryResponse(
                        has_permission=True,
                        message=f"表 {table_name} 不支持按唛头查询",
                        records=[],
                        record_count=0,
                        available_fields=self._get_available_fields(model),
                        tables=self._get_available_tables(),
                    )

            # 4. 转换结果
            result_records = [self._convert_record_to_dict(r) for r in records]

            return TableQueryResponse(
                has_permission=True,
                message=f"查询到 {len(result_records)} 条记录" if result_records else "未找到符合条件的记录",
                records=result_records,
                record_count=len(result_records),
                available_fields=self._get_available_fields(model),
                tables=self._get_available_tables(),
            )

        except Exception as e:
            import traceback
            print(f"Table query error: {str(e)}")
            traceback.print_exc()
            return TableQueryResponse(
                has_permission=True,
                message=f"查询出错: {str(e)}",
                records=[],
                record_count=0,
                available_fields=self._get_available_fields(model),
                tables=self._get_available_tables(),
            )

    def get_initial_data(self) -> TableQueryResponse:
        """获取初始数据（表列表和字段）"""
        if not self._is_authorized():
            return TableQueryResponse(
                has_permission=False,
                message="您没有权限使用表查询功能",
                records=[],
                record_count=0,
                available_fields=[],
                tables=[],
            )

        return TableQueryResponse(
            has_permission=True,
            message="请选择表和查询条件",
            records=[],
            record_count=0,
            available_fields=[],
            tables=self._get_available_tables(),
        )

