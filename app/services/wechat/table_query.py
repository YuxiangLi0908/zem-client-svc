from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from app.data_models.db.user import Customer, AuthUser
from app.data_models.db.container import Container
from app.data_models.db.order import Order
from app.data_models.db.warehouse import Warehouse
from app.data_models.db.vessel import Vessel
from app.data_models.db.retrieval import Retrieval
from app.data_models.db.offload import Offload
from app.data_models.db.shipment import Shipment
from app.data_models.db.fleet import Fleet
from app.data_models.db.packing_list import PackingList
from app.data_models.wechat.order_tracking import TableQueryResponse


class TableQuery:

    AUTHORIZED_USERS = {"sangwei", "yuxiang.li", "qyj"}

    CONTAINER_JOIN_DIRECT = "direct"
    CONTAINER_JOIN_THROUGH_ORDER = "through_order"

    FK_DISPLAY_CONFIG = {
        "Order": {
            "customer_name_id": {"model": Customer, "display_field": "zem_name", "label": "customer_name"},
            "container_number_id": {"model": Container, "display_field": "container_number", "label": "container_number"},
            "warehouse_id": {"model": Warehouse, "display_field": "name", "label": "warehouse"},
            "vessel_id_id": {"model": Vessel, "display_field": "vessel_id", "label": "vessel"},
            "retrieval_id_id": {"model": Retrieval, "display_field": "retrieval_id", "label": "retrieval"},
            "offload_id_id": {"model": Offload, "display_field": "offload_id", "label": "offload"},
            "shipment_id_id": {"model": Shipment, "display_field": "shipment_batch_number", "label": "shipment"},
        },
        "Pallet": {
            "packing_list_id": {"model": PackingList, "display_field": "id", "label": "packing_list"},
            "container_number_id": {"model": Container, "display_field": "container_number", "label": "container_number"},
            "shipment_batch_number_id": {"model": Shipment, "display_field": "shipment_batch_number", "label": "shipment_batch_number"},
            "master_shipment_batch_number_id": {"model": Shipment, "display_field": "shipment_batch_number", "label": "master_shipment_batch_number"},
        },
        "PackingList": {
            "container_number_id": {"model": Container, "display_field": "container_number", "label": "container_number"},
            "shipment_batch_number_id": {"model": Shipment, "display_field": "shipment_batch_number", "label": "shipment_batch_number"},
            "master_shipment_batch_number_id": {"model": Shipment, "display_field": "shipment_batch_number", "label": "master_shipment_batch_number"},
        },
        "Shipment": {
            "fleet_number_id": {"model": Fleet, "display_field": "fleet_number", "label": "fleet_number"},
        },
    }

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
                {"name": "container_number", "label": "柜号", "type": "string"},
                {"name": "id", "label": "ID", "type": "integer"},
            ],
        },
        "Order": {
            "model_module": "app.data_models.db.order",
            "model_class": "Order",
            "container_join": CONTAINER_JOIN_DIRECT,
            "search_fields": [
                {"name": "container_number", "label": "柜号", "type": "string"},
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "order_id", "label": "Order ID", "type": "string"},
            ],
        },
        "Pallet": {
            "model_module": "app.data_models.db.pallet",
            "model_class": "Pallet",
            "container_join": CONTAINER_JOIN_DIRECT,
            "search_fields": [
                {"name": "container_number", "label": "柜号", "type": "string"},
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "PO_ID", "label": "PO ID", "type": "string"},
            ],
        },
        "PackingList": {
            "model_module": "app.data_models.db.packing_list",
            "model_class": "PackingList",
            "container_join": CONTAINER_JOIN_DIRECT,
            "search_fields": [
                {"name": "container_number", "label": "柜号", "type": "string"},
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "PO_ID", "label": "PO ID", "type": "string"},
            ],
        },
        "Retrieval": {
            "model_module": "app.data_models.db.retrieval",
            "model_class": "Retrieval",
            "container_join": CONTAINER_JOIN_THROUGH_ORDER,
            "search_fields": [
                {"name": "container_number", "label": "柜号", "type": "string"},
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "retrieval_id", "label": "Retrieval ID", "type": "string"},
            ],
        },
        "Offload": {
            "model_module": "app.data_models.db.offload",
            "model_class": "Offload",
            "container_join": CONTAINER_JOIN_THROUGH_ORDER,
            "search_fields": [
                {"name": "container_number", "label": "柜号", "type": "string"},
                {"name": "id", "label": "ID", "type": "integer"},
                {"name": "offload_id", "label": "Offload ID", "type": "string"},
            ],
        },
        "Vessel": {
            "model_module": "app.data_models.db.vessel",
            "model_class": "Vessel",
            "container_join": CONTAINER_JOIN_THROUGH_ORDER,
            "search_fields": [
                {"name": "container_number", "label": "柜号", "type": "string"},
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

    def _convert_record_to_dict(self, record, table_name: str = "") -> Dict:
        if not record:
            return {}

        result = {}
        mapper = inspect(type(record))

        fk_config = self.FK_DISPLAY_CONFIG.get(table_name, {})

        for column in mapper.columns:
            value = getattr(record, column.key)
            if column.key in fk_config:
                display_value = self._resolve_fk_display(column.key, value, fk_config[column.key])
                label = fk_config[column.key]["label"]
                if display_value is not None:
                    result[label] = display_value
                elif value is not None:
                    result[label] = value
            else:
                if hasattr(value, "isoformat"):
                    result[column.key] = value.isoformat()
                elif isinstance(value, (int, float, str, bool, type(None))):
                    result[column.key] = value
                else:
                    result[column.key] = str(value)

        return result

    def _resolve_fk_display(self, fk_field: str, fk_value, config: Dict):
        if fk_value is None:
            return None
        try:
            model = config["model"]
            display_field = config["display_field"]
            related = self.db_session.query(model).filter(model.id == fk_value).first()
            if related:
                return getattr(related, display_field, None)
        except Exception:
            pass
        return None

    def _query_by_container_number(self, model, table_name: str, search_value: str):
        config = self.TABLE_CONFIG.get(table_name, {})
        join_type = config.get("container_join")

        if join_type == self.CONTAINER_JOIN_DIRECT:
            return (
                self.db_session.query(model)
                .join(Container, Container.id == model.container_number_id)
                .filter(Container.container_number.ilike(f"%{search_value}%"))
                .limit(50)
                .all()
            )
        elif join_type == self.CONTAINER_JOIN_THROUGH_ORDER:
            fk_map = {
                "Retrieval": Order.retrieval_id_id,
                "Offload": Order.offload_id_id,
                "Vessel": Order.vessel_id_id,
            }
            order_fk = fk_map.get(table_name)
            if not order_fk:
                return []
            return (
                self.db_session.query(model)
                .join(Order, order_fk == model.id)
                .join(Container, Container.id == Order.container_number_id)
                .filter(Container.container_number.ilike(f"%{search_value}%"))
                .limit(50)
                .all()
            )
        return []

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
            if search_field == "container_number":
                records = self._query_by_container_number(model, table_name, search_value)
            elif search_field == "id":
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

            result_records = [self._convert_record_to_dict(r, table_name) for r in records]

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
