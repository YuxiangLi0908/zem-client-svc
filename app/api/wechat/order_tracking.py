
"""
微信小程序订单追踪API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.services.wechat.order_history import OrderTracking
from app.services.user_auth import get_current_user
from app.services.db_session import db_session
from app.data_models.db.user import User
from app.data_models.wechat.order_tracking import OrderResponse, OrderTrackingRequest

router = APIRouter()


@router.post("/order_tracking", response_model=OrderResponse, name="wechat_order_tracking")
async def get_order_full_history(
    request: OrderTrackingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> OrderResponse:
    """
    微信小程序订单追踪接口

    支持柜号或唛头查询
    """
    import traceback
    try:
        query = request.container_number.strip()

        order_tracking = OrderTracking(
            user=current_user,
            query=query,
            db_session=db,
        )
        result = order_tracking.build_order_full_history()
        return result
    except Exception as e:
        print(f"[Error] 查询失败: {str(e)}")
        print(traceback.format_exc())
        return OrderResponse(
            preport_timenode=None,
            postport_timenode=None,
            has_permission=True,
            message=f"查询失败: {str(e)}"
        )

