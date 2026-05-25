from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from app.data_models.db.user import Customer, AuthUser
from app.data_models.wechat.order_tracking import TableQueryResponse


class TableQuery:

    AUTHORIZED_USERS = {"sangwei", "yuxiang.li", "qyj"}

    TABLE_CONFIG = {
        "Shipment": {
            "model_module": "app.data_models.db.shipment",
            "model_class": "Shipment",
            "search_fields": [
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "appointment_id", "label": "Appointment ID", "type": "string"},
                {"name": "shipment_batch_number", "label": "Shipment Batch Number", "type": "string"},
            ],
        },
        "Fleet": {
            "model_module": "app.data_models.db.fleet",
            "model_class": "Fleet",
            "search_fields": [
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "fleet_number", "label": "Fleet Number", "type": "string"},
                {"name": "pickup_number", "label": "Pickup Number", "type": "string"},
            ],
        },
        "Container": {
            "model_module": "app.data_models.db.container",
            "model_class": "Container",
            "search_fields": [
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "container_number", "label": "柜号", "type": "string"},
            ],
        },
        "Order": {
            "model_module": "app.data_models.db.order",
            "model_class": "Order",
            "search_fields": [
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "order_id", "label": "Order ID", "type": "string"},
            ],
        },
        "Pallet": {
            "model_module": "app.data_models.db.pallet",
            "model_class": "Pallet",
            "search_fields": [
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "PO_ID", "label": "PO ID", "type": "string"},
            ],
        },
        "PackingList": {
            "model_module": "app.data_models.db.packing_list",
            "model_class": "PackingList",
            "search_fields": [
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "PO_ID", "label": "PO ID", "type": "string"},
            ],
        },
        "Retrieval": {
            "model_module": "app.data_models.db.retrieval",
            "model_class": "Retrieval",
            "search_fields": [
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "retrieval_id", "label": "Retrieval ID", "type": "string"},
            ],
        },
        "Offload": {
            "model_module": "app.data_models.db.offload",
            "model_class": "Offload",
            "search_fields": [
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "offload_id", "label": "Offload ID", "type": "string"},
            ],
        },
        "Vessel": {
            "model_module": "app.data_models.db.vessel",
            "model_class": "Vessel",
            "search_fields": [
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "vessel_id", "label": "Vessel ID", "type": "string"},
            ],
        },
        "Customer": {
            "model_module": "app.data_models.db.user",
            "model_class": "Customer",
            "search_fields": [
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "zem_name", "label": "ZEM Name", "type": "string"},
            ],
        },
    }

    def __init__(self, user: Customer | AuthUser, db_session: Session) -> None:
        self.user = user
        self.db_session = db_session

    def _get_username(self) -> str:
        if isinstance(self.user, AuthUser):
            return self.user.username or ""
        if isinstance(self.user, Customer):
            return self.user.username or ""
        return ""

    def _is_authorized(self) -> bool:
        username = self._get_username()
        return username in self.AUTHORIZED_USERS

    def _get_available_tables(self) -> List[Dict]:
        tables = []
        for table_name, config in self.TABLE_CONFIG.items():
            tables.append({
                "name": table_name,
                "search_fields": config["search_fields"],
            })
        return tables

    def _get_model_by_name(self, table_name: str):
        config = self.TABLE_CONFIG.get(table_name)
        if not config:
            return None
        import importlib
        module = importlib.import_module(config["model_module"])
        return getattr(module, config["model_class"])

    def _get_search_fields(self, table_name: str) -> List[Dict]:
        config = self.TABLE_CONFIG.get(table_name)
        if not config:
            return []
        return config["search_fields"]

    def _convert_record_to_dict(self, record) -> Dict:
        if not record:
            return {}

        result = {}
        mapper = inspect(type(record))

        for column in mapper.columns:
            value = getattr(record, column.key)
            if hasattr(value, "isoformat"):
                result[column.key] = value.isoformat()
            elif isinstance(value, (int, float, str, bool, type(None))):
                result[column.key] = value
            else:
                result[column.key] = str(value)

        return result

    def query_table(self, table_name: str, search_field: str, search_value: str) -> TableQueryResponse:
        if not self._is_authorized():
            return TableQueryResponse(
                has_permission=False,
                message="您没有权限使用表查询功能",
                records=[],
                record_count=0,
                available_fields=[],
                tables=[],
            )

        model = self._get_model_by_name(table_name)
        if not model:
            return TableQueryResponse(
                has_permission=True,
                message=f"未找到表 {table_name}",
                records=[],
                record_count=0,
                available_fields=self._get_search_fields(table_name),
                tables=self._get_available_tables(),
            )

        search_fields = self._get_search_fields(table_name)
        valid_field_names = [f["name"] for f in search_fields]
        if search_field not in valid_field_names:
            return TableQueryResponse(
                has_permission=True,
                message=f"表 {table_name} 不支持按 {search_field} 查询",
                records=[],
                record_count=0,
                available_fields=search_fields,
                tables=self._get_available_tables(),
            )

        query = self.db_session.query(model)
        records = []

        try:
            if search_field == "id":
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
                        available_fields=search_fields,
                        tables=self._get_available_tables(),
                    )
            else:
                column_attr = getattr(model, search_field, None)
                if column_attr is None:
                    return TableQueryResponse(
                        has_permission=True,
                        message=f"表 {table_name} 不存在字段 {search_field}",
                        records=[],
                        record_count=0,
                        available_fields=search_fields,
                        tables=self._get_available_tables(),
                    )
                records = query.filter(column_attr.ilike(f"%{search_value}%")).limit(50).all()

            result_records = [self._convert_record_to_dict(r) for r in records]

            return TableQueryResponse(
                has_permission=True,
                message=f"查询到 {len(result_records)} 条记录" if result_records else "未找到符合条件的记录",
                records=result_records,
                record_count=len(result_records),
                available_fields=search_fields,
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
                available_fields=search_fields,
                tables=self._get_available_tables(),
            )

    def get_initial_data(self) -> TableQueryResponse:
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
