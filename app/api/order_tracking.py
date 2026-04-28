from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.data_models.db.user import User
from app.data_models.order_tracking import OrderResponse, OrderTrackingRequest
from app.services.db_session import db_session
from app.services.order_history import OrderTracking
from app.services.user_auth import get_current_user
from app.services.order_history import BatchOrderTracking

router = APIRouter()


@router.post("/order_tracking", response_model=OrderResponse, name="order_tracking")
async def get_order_full_history(
    request: OrderTrackingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> OrderResponse:
    
    try:
        #container_number = request.container_number.strip()
        order_tracking = OrderTracking(
            user=current_user, 
            db_session=db,
            container_number=request.container_number.strip()
        )
        result = order_tracking.build_order_full_history()
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise


@router.get("/user_containers", response_model=list[OrderResponse], name="user_containers")
async def get_user_containers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> list[OrderResponse]:
    import traceback
    from app.data_models.db.container import Container
    from app.data_models.db.order import Order
    from datetime import datetime, timedelta
    
    try:
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        print(f"[get_user_containers] User: username={current_user.username}, zem_name={current_user.zem_name}, zem_code={getattr(current_user, 'zem_code', 'N/A')}")
        
        # 获取用户过去六个月内的所有容器号
        container_query = db.query(Container.container_number).join(Order)
        
        if current_user.username != "superuser":
            container_query = container_query.join(User).filter(
                User.zem_name == current_user.zem_name,
                Order.created_at >= six_months_ago
            )
        else:
            container_query = container_query.filter(
                Order.created_at >= six_months_ago
            )
        
        container_query = container_query.distinct()
        container_numbers = [cn for (cn,) in container_query.all() if cn]
        
        if not container_numbers:
            return []
        
        # 使用批量查询
        batch_tracking = BatchOrderTracking(
            user=current_user,
            db_session=db
        )
        
        result = batch_tracking.build_all_orders(container_numbers)
        return result
        
    except Exception as e:
        error_detail = f"User: {current_user.username}, zem_name: {current_user.zem_name}, zem_code: {getattr(current_user, 'zem_code', 'N/A')}, Error: {str(e)}"
        print(f"[get_user_containers] Error: {error_detail}")
        print(traceback.format_exc())
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Internal server error: {error_detail}")
