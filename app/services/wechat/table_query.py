from typing import List, Dict, Optional
from io import BytesIO
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
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
from app.data_models.db.invoice_v2 import Invoicev2, InvoiceStatusv2, InvoiceItemv2
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
        "Invoicev2": {
            "customer_id": {"model": Customer, "display_field": "zem_name", "label": "customer"},
            "container_number_id": {"model": Container, "display_field": "container_number", "label": "container_number"},
        },
        "InvoiceStatusv2": {
            "container_number_id": {"model": Container, "display_field": "container_number", "label": "container_number"},
            "invoice_id": {"model": Invoicev2, "display_field": "invoice_number", "label": "invoice_number"},
        },
        "InvoiceItemv2": {
            "container_number_id": {"model": Container, "display_field": "container_number", "label": "container_number"},
            "invoice_number_id": {"model": Invoicev2, "display_field": "invoice_number", "label": "invoice_number"},
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
        "Invoicev2": {
            "model_module": "app.data_models.db.invoice_v2",
            "model_class": "Invoicev2",
            "container_join": CONTAINER_JOIN_DIRECT,
            "search_fields": [
                {"name": "invoice_number", "label": "Invoice Number", "type": "string"},
                {"name": "container_number", "label": "柜号", "type": "string"},
                {"name": "id", "label": "ID", "type": "integer"},
            ],
        },
        "InvoiceStatusv2": {
            "model_module": "app.data_models.db.invoice_v2",
            "model_class": "InvoiceStatusv2",
            "container_join": CONTAINER_JOIN_DIRECT,
            "search_fields": [
                {"name": "invoice_number", "label": "Invoice Number", "type": "string"},
                {"name": "container_number", "label": "柜号", "type": "string"},
                {"name": "id", "label": "ID", "type": "integer"},
            ],
        },
        "InvoiceItemv2": {
            "model_module": "app.data_models.db.invoice_v2",
            "model_class": "InvoiceItemv2",
            "container_join": CONTAINER_JOIN_DIRECT,
            "search_fields": [
                {"name": "invoice_number", "label": "Invoice Number", "type": "string"},
                {"name": "container_number", "label": "柜号", "type": "string"},
                {"name": "id", "label": "ID", "type": "integer"},
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
                if search_field == "invoice_number" and table_name in ("InvoiceStatusv2", "InvoiceItemv2"):
                    invoice_fk = InvoiceStatusv2.invoice_id if table_name == "InvoiceStatusv2" else InvoiceItemv2.invoice_number_id
                    records = (
                        self.db_session.query(model)
                        .join(Invoicev2, Invoicev2.id == invoice_fk)
                        .filter(Invoicev2.invoice_number.ilike(f"%{search_value}%"))
                        .limit(50)
                        .all()
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

            if table_name == "Invoicev2":
                for i, r in enumerate(records):
                    item_count = self.db_session.query(InvoiceItemv2).filter(
                        InvoiceItemv2.invoice_number_id == r.id
                    ).count()
                    result_records[i]["invoice_item_count"] = item_count

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

    def execute_sql(self, sql: str, output_format: str = "display") -> Dict:
        if not self._is_authorized():
            return {"success": False, "message": "您没有权限使用SQL查询功能"}

        sql_stripped = sql.strip()
        if not sql_stripped:
            return {"success": False, "message": "SQL语句不能为空"}

        sql_upper = sql_stripped.upper().lstrip()
        if not sql_upper.startswith("SELECT"):
            return {"success": False, "message": "仅支持SELECT查询语句"}

        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "EXEC", "EXECUTE"]
        sql_check = sql_upper.split()
        for kw in forbidden_keywords:
            if kw in sql_check:
                return {"success": False, "message": f"不允许执行{kw}操作"}

        try:
            result = self.db_session.execute(text(sql_stripped))
            columns = list(result.keys())
            rows = result.fetchall()

            if output_format == "excel":
                return self._generate_excel(columns, rows)

            records = []
            for row in rows:
                record = {}
                for i, col in enumerate(columns):
                    val = row[i]
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    elif val is None:
                        val = ""
                    else:
                        val = str(val)
                    record[col] = val
                records.append(record)

            return {
                "success": True,
                "message": f"查询成功，共{len(records)}条记录",
                "columns": columns,
                "records": records,
                "record_count": len(records),
            }
        except Exception as e:
            return {"success": False, "message": f"SQL执行失败: {str(e)}"}

    def _generate_excel(self, columns: list, rows: list) -> Dict:
        try:
            import pandas as pd

            data = []
            for row in rows:
                row_data = []
                for i, col in enumerate(columns):
                    val = row[i]
                    if hasattr(val, "isoformat"):
                        val = val.isoformat()
                    elif val is None:
                        val = ""
                    row_data.append(val)
                data.append(row_data)

            df = pd.DataFrame(data, columns=columns)
            buffer = BytesIO()
            df.to_excel(buffer, index=False, engine="openpyxl")
            buffer.seek(0)

            import base64
            excel_base64 = base64.b64encode(buffer.read()).decode("utf-8")

            return {
                "success": True,
                "message": f"导出成功，共{len(rows)}条记录",
                "output_format": "excel",
                "excel_data": excel_base64,
                "record_count": len(rows),
            }
        except Exception as e:
            return {"success": False, "message": f"Excel生成失败: {str(e)}"}

    def delete_shipment(self, shipment_id: int) -> Dict:
        if not self._is_authorized():
            return {"success": False, "message": "您没有权限执行删除操作"}

        from app.data_models.db.pallet import Pallet
        from app.data_models.db.packing_list import PackingList
        from app.data_models.db.order import Order

        try:
            shipment = self.db_session.query(Shipment).filter(Shipment.id == shipment_id).first()
            if not shipment:
                return {"success": False, "message": f"未找到ID为{shipment_id}的Shipment记录"}

            pallets = self.db_session.query(Pallet).filter(
                (Pallet.shipment_batch_number_id == shipment_id) |
                (Pallet.master_shipment_batch_number_id == shipment_id)
            ).all()
            for p in pallets:
                if p.shipment_batch_number_id == shipment_id:
                    p.shipment_batch_number_id = None
                if p.master_shipment_batch_number_id == shipment_id:
                    p.master_shipment_batch_number_id = None

            packing_lists = self.db_session.query(PackingList).filter(
                (PackingList.shipment_batch_number_id == shipment_id) |
                (PackingList.master_shipment_batch_number_id == shipment_id)
            ).all()
            for pl in packing_lists:
                if pl.shipment_batch_number_id == shipment_id:
                    pl.shipment_batch_number_id = None
                if pl.master_shipment_batch_number_id == shipment_id:
                    pl.master_shipment_batch_number_id = None

            orders = self.db_session.query(Order).filter(Order.shipment_id_id == shipment_id).all()
            for o in orders:
                o.shipment_id_id = None

            fleet_id = shipment.fleet_number_id

            self.db_session.delete(shipment)

            if fleet_id:
                fleet = self.db_session.query(Fleet).filter(Fleet.id == fleet_id).first()
                if fleet:
                    self.db_session.delete(fleet)

            self.db_session.commit()

            msg = f"已删除Shipment记录(ID={shipment_id})"
            if fleet_id:
                msg += f"，已删除关联Fleet记录(ID={fleet_id})"
            return {"success": True, "message": msg}
        except Exception as e:
            self.db_session.rollback()
            return {"success": False, "message": f"删除失败: {str(e)}"}
