
"""
微信小程序表查询API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.wechat.table_query import TableQuery
from app.services.user_auth import get_current_user
from app.services.db_session import db_session
from app.data_models.db.user import Customer, AuthUser
from app.data_models.wechat.order_tracking import TableQueryResponse, TableQueryRequest, SqlQueryRequest, SqlQueryResponse, DeleteShipmentRequest, DeleteShipmentResponse, DbOperationRequest, DbOperationResponse

router = APIRouter()


@router.get("/table_query/init", response_model=TableQueryResponse, name="wechat_table_query_init")
async def get_table_query_init(
    current_user: Customer | AuthUser = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> TableQueryResponse:
    """
    获取表查询初始数据（表列表）
    """
    table_query = TableQuery(user=current_user, db_session=db)
    return table_query.get_initial_data()


@router.post("/table_query", response_model=TableQueryResponse, name="wechat_table_query")
async def execute_table_query(
    request: TableQueryRequest,
    current_user: Customer | AuthUser = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> TableQueryResponse:
    """
    执行表查询
    """
    import traceback
    try:
        table_query = TableQuery(user=current_user, db_session=db)
        return table_query.query_table(
            table_name=request.table_name,
            search_field=request.search_field,
            search_value=request.search_value,
        )
    except Exception as e:
        print(f"[Error] 表查询失败: {str(e)}")
        print(traceback.format_exc())
        return TableQueryResponse(
            has_permission=True,
            message=f"查询失败: {str(e)}",
            records=[],
            record_count=0,
            available_fields=[],
            tables=[],
        )


@router.post("/table_query/sql", response_model=SqlQueryResponse, name="wechat_sql_query")
async def execute_sql_query(
    request: SqlQueryRequest,
    current_user: Customer | AuthUser = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> SqlQueryResponse:
    table_query = TableQuery(user=current_user, db_session=db)
    result = table_query.execute_sql(sql=request.sql, output_format=request.output_format)
    return SqlQueryResponse(**result)


@router.post("/table_query/delete_shipment", response_model=DeleteShipmentResponse, name="wechat_delete_shipment")
async def delete_shipment(
    request: DeleteShipmentRequest,
    current_user: Customer | AuthUser = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> DeleteShipmentResponse:
    table_query = TableQuery(user=current_user, db_session=db)
    result = table_query.delete_shipment(shipment_id=request.shipment_id)
    return DeleteShipmentResponse(**result)


@router.post("/table_query/db_operation", response_model=DbOperationResponse, name="wechat_db_operation")
async def execute_db_operation(
    request: DbOperationRequest,
    current_user: Customer | AuthUser = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> DbOperationResponse:
    table_query = TableQuery(user=current_user, db_session=db)
    result = table_query.execute_db_operation(
        table_name=request.table_name,
        operation=request.operation,
        conditions=[c.model_dump() for c in request.conditions],
        update_field=request.update_field,
        update_value=request.update_value,
        output_format=request.output_format,
    )
    return DbOperationResponse(**result)


@router.get("/table_query/columns/{table_name}", response_model=DbOperationResponse, name="wechat_table_columns")
async def get_table_columns(
    table_name: str,
    current_user: Customer | AuthUser = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> DbOperationResponse:
    table_query = TableQuery(user=current_user, db_session=db)
    result = table_query.get_table_columns(table_name=table_name)
    return DbOperationResponse(**result)

