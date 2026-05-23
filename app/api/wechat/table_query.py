
"""
微信小程序表查询API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.wechat.table_query import TableQuery
from app.services.user_auth import get_current_user
from app.services.db_session import db_session
from app.data_models.db.user import Customer, AuthUser
from app.data_models.wechat.order_tracking import TableQueryResponse, TableQueryRequest

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

