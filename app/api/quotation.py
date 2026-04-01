from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text, or_
from sqlalchemy.orm import Session
from pydantic import BaseModel
import traceback

from app.services.db_session import db_session
from app.services.user_auth import get_current_user
from app.data_models.db.user import User
from app.data_models.db.quotation_master import QuotationMaster
from app.data_models.db.fee_detail import FeeDetail

router = APIRouter()


class QuotationRequest(BaseModel):
    destination: str
    cbm: float
    pallets: int
    container_type: str


class QuotationItem(BaseModel):
    warehouse: str
    type: str
    price: Optional[float] = None
    message: Optional[str] = None


class QuotationResponse(BaseModel):
    quotations: list[QuotationItem]


@router.post("/query_quotation", response_model=QuotationResponse)
async def query_quotation(
    request: QuotationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> QuotationResponse:
    """
    询价API
    遍历三个仓库(NJ/SAV/LA)，每个仓库查询转运和组合柜两种报价
    """
    try:
        print('[query_quotation] ===== 开始询价 =====')
        print(f'[query_quotation] 当前用户: {current_user.username}')
        print(f'[query_quotation] 请求参数 - 仓点: {request.destination}, CBM: {request.cbm}, 板数: {request.pallets}, 柜型: {request.container_type}')
        
        warehouses = ["NJ", "SAV", "LA"]
        quotation_types = ["转运", "组合柜"]
        results = []

        vessel_etd = date.today()
        customer_name = current_user.username
        
        print(f'[query_quotation] 查询日期: {vessel_etd}')

        db.rollback()
        
        quotation_master = _get_quotation_master(db, customer_name, vessel_etd)
        if not quotation_master:
            print('[query_quotation] 未找到报价主表，所有查询都失败')
            for warehouse in warehouses:
                for quote_type in quotation_types:
                    results.append(QuotationItem(
                        warehouse=warehouse,
                        type=quote_type,
                        price=None,
                        message="没有报价"
                    ))
            return QuotationResponse(quotations=results)
        
        print(f'[query_quotation] 找到报价主表 - ID: {quotation_master["id"]}, 文件名: {quotation_master["filename"]}')

        for warehouse in warehouses:
            for quote_type in quotation_types:
                print(f'\n[query_quotation] 正在查询 - 仓库: {warehouse}, 类型: {quote_type}')
                price = None
                message = None

                try:
                    price = _get_quotation_price(
                        db=db,
                        quotation_master=quotation_master,
                        warehouse=warehouse,
                        quote_type=quote_type,
                        request=request
                    )

                    if price is not None:
                        if quote_type == "转运":
                            price = price * request.pallets
                            print(f'[query_quotation] 转运价格计算: 单价 x 板数 = {price}')
                        print(f'[query_quotation] 查询成功 - 价格: {price}')
                    else:
                        message = "没有报价"
                        print(f'[query_quotation] 查询结果: 没有报价')

                except Exception as e:
                    db.rollback()
                    message = f"查询失败: {str(e)}"
                    print(f'[query_quotation] 查询异常: {str(e)}')
                    print(traceback.format_exc())

                results.append(QuotationItem(
                    warehouse=warehouse,
                    type=quote_type,
                    price=price,
                    message=message
                ))

        print('\n[query_quotation] ===== 询价完成 =====')
        return QuotationResponse(quotations=results)

    except Exception as e:
        print(f'[query_quotation] 整体异常: {str(e)}')
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"询价失败: {str(e)}")


def _get_quotation_price(
    db: Session,
    quotation_master,
    warehouse: str,
    quote_type: str,
    request: QuotationRequest
) -> Optional[float]:
    """
    获取报价价格
    """
    try:
        print(f'[_get_quotation_price] 开始获取报价 - 仓库: {warehouse}, 类型: {quote_type}')
        
        fee_detail = _get_fee_detail(db, quotation_master['id'], warehouse, quote_type)
        if not fee_detail:
            print(f'[_get_quotation_price] 未找到费用明细')
            return None
        
        print(f'[_get_quotation_price] 找到费用明细 - ID: {fee_detail["id"]}')

        price = _calculate_price(fee_detail, quote_type, warehouse, request)
        print(f'[_get_quotation_price] 计算结果: {price}')
        return price

    except Exception as e:
        print(f"[_get_quotation_price] 异常: {str(e)}")
        print(traceback.format_exc())
        return None


def _get_quotation_master(db: Session, customer_name: str, vessel_etd: date):
    """
    获取报价表
    """
    try:
        print(f'[_get_quotation_master] 开始查询报价主表 - 用户: {customer_name}, 日期: {vessel_etd}')
        
        db.rollback()
        
        print(f'[_get_quotation_master] 先查询专属用户报价')
        query = text("""
            SELECT id, filename
            FROM warehouse_quotationMaster
            WHERE effective_date <= :vessel_etd
            AND is_user_exclusive = true
            AND exclusive_user = :customer_name
            AND quote_type = 'receivable'
            ORDER BY effective_date DESC
            LIMIT 1
        """)
        result = db.execute(query, {
            'vessel_etd': vessel_etd,
            'customer_name': customer_name
        }).fetchone()
        
        if not result:
            print(f'[_get_quotation_master] 未找到专属用户报价，查询公共报价')
            query = text("""
                SELECT id, filename
                FROM warehouse_quotationMaster
                WHERE effective_date <= :vessel_etd
                AND is_user_exclusive = false
                AND quote_type = 'receivable'
                ORDER BY effective_date DESC
                LIMIT 1
            """)
            result = db.execute(query, {
                'vessel_etd': vessel_etd
            }).fetchone()

        if result:
            print(f'[_get_quotation_master] 找到报价主表 - ID: {result[0]}, 文件名: {result[1]}')
            return {'id': result[0], 'filename': result[1]}
        else:
            print(f'[_get_quotation_master] 未找到任何报价主表')
            return None

    except Exception as e:
        print(f"[_get_quotation_master] 异常: {str(e)}")
        print(traceback.format_exc())
        db.rollback()
        return None


def _get_fee_detail(db: Session, quotation_id: int, warehouse: str, quote_type: str):
    """
    获取费用明细
    """
    try:
        print(f'[_get_fee_detail] 开始查询费用明细 - 报价ID: {quotation_id}, 仓库: {warehouse}, 类型: {quote_type}')
        
        fee_types_map = {
            "NJ": {
                "转运": "NJ_PUBLIC",
                "组合柜": "NJ_COMBINA"
            },
            "SAV": {
                "转运": "SAV_PUBLIC",
                "组合柜": "SAV_COMBINA"
            },
            "LA": {
                "转运": "LA_PUBLIC",
                "组合柜": "LA_COMBINA"
            }
        }

        fee_type = fee_types_map.get(warehouse, {}).get(quote_type)
        print(f'[_get_fee_detail] 映射的费用类型: {fee_type}')
        
        if not fee_type:
            print(f'[_get_fee_detail] 未找到匹配的费用类型')
            return None

        db.rollback()
        
        query = text("""
            SELECT id, details, niche_warehouse
            FROM warehouse_feeDetail
            WHERE quotation_id_id = :quotation_id
            AND fee_type = :fee_type
            LIMIT 1
        """)
        result = db.execute(query, {
            'quotation_id': quotation_id,
            'fee_type': fee_type
        }).fetchone()

        if result:
            print(f'[_get_fee_detail] 找到费用明细 - ID: {result[0]}')
            if result[1]:
                print(f'[_get_fee_detail] 有details数据')
            if result[2]:
                print(f'[_get_fee_detail] 有niche_warehouse数据')
            return {'id': result[0], 'details': result[1], 'niche_warehouse': result[2]}
        else:
            print(f'[_get_fee_detail] 未找到费用明细 - 报价ID: {quotation_id}, 费用类型: {fee_type}')
            return None

    except Exception as e:
        print(f"[_get_fee_detail] 异常: {str(e)}")
        print(traceback.format_exc())
        db.rollback()
        return None


def _calculate_price(fee_detail, quote_type: str, warehouse: str, request: QuotationRequest) -> Optional[float]:
    """
    计算价格
    """
    try:
        
        print(f'[_calculate_price] 开始计算价格 - 类型: {quote_type}')
        
        if not fee_detail or not fee_detail['details']:
            print(f'[_calculate_price] fee_detail或details为空')
            return None

        details = fee_detail.get('details')
        print(f'[_calculate_price] 解析details成功')
        
        if quote_type == "组合柜":
            print(f'[_calculate_price] 调用组合柜价格计算')
            return _calculate_combina_price(details, request)
        else:
            print(f'[_calculate_price] 调用转运价格计算')
            return _calculate_transfer_price(details, fee_detail, warehouse, request)

    except Exception as e:
        print(f"[_calculate_price] 异常: {str(e)}")
        print(traceback.format_exc())
        return None

def _process_destination(destination_origin):
        """处理目的地字符串"""
        def clean_all_spaces(s):
            if not s:  # 处理None/空字符串
                return ""
            # 匹配所有空格类型：
            # \xa0 非中断空格 | \u3000 中文全角空格 | \s 普通空格/制表符/换行等
            import re
            cleaned = re.sub(r'[\xa0\u3000\s]+', '', str(s))
            return cleaned
        
        destination_origin = str(destination_origin)

        # 匹配模式：按"改"或"送"分割，分割符放在第一组的末尾
        if "改" in destination_origin or "送" in destination_origin:
            # 找到第一个"改"或"送"的位置
            first_change_pos = min(
                (destination_origin.find(char) for char in ["改", "送"] 
                if destination_origin.find(char) != -1),
                default=-1
            )
            
            if first_change_pos != -1:
                # 第一部分：到第一个"改"或"送"（包含分隔符）
                first_part = destination_origin[:first_change_pos + 1]
                # 第二部分：剩下的部分
                second_part = destination_origin[first_change_pos + 1:]
                
                # 处理第一部分：按"-"分割取后面的部分
                if "-" in first_part:
                    if first_part.upper().startswith("UPS-"):
                        first_result = first_part
                    else:
                        first_result = first_part.split("-", 1)[1]
                else:
                    first_result = first_part
                
                # 处理第二部分：按"-"分割取后面的部分
                if "-" in second_part:
                    if second_part.upper().startswith("UPS-"):
                        second_result = second_part
                    else:
                        second_result = second_part.split("-", 1)[1]
                else:
                    second_result = second_part
                
                second_result = second_result.replace(" ", "").upper()
                return clean_all_spaces(first_result), clean_all_spaces(second_result)
            else:
                raise ValueError(first_change_pos)
        
        # 如果不包含"改"或"送"或者没有找到
        # 只处理第二部分（假设第一部分为空）
        if "-" in destination_origin:
            if destination_origin.upper().startswith("UPS-"):
                second_result = destination_origin
            else:
                second_result = destination_origin.split("-", 1)[1]
            
        else:
            second_result = destination_origin
        
        second_result = second_result.replace(" ", "").upper()
        return None, clean_all_spaces(second_result)
def _calculate_combina_price(details: dict, request: QuotationRequest) -> Optional[float]:
    """
    计算组合柜价格
    """
    try:
        print(f'[_calculate_combina_price] 开始计算组合柜价格 - 柜型: {request.container_type}')
        print(f'[_calculate_combina_price] details内容: {details}')
        
        container_type_temp = 0 if "40" in request.container_type else 1
        
        destination_origin, destination = _process_destination(request.destination)
        
        # 检查是否属于组合区域
        price = 0
        is_combina_region = False
        region = None
        for region, region_data in details.items():
            for item in region_data:
                rule_locations = item.get("location", [])
                if isinstance(rule_locations, str):
                    rule_locations = [rule_locations] # 统一转成列表处理

                if any(destination == loc.replace(" ", "").upper() for loc in rule_locations):
                    is_combina_region = True
                    price = item["prices"][container_type_temp]
                    region = region
                    break
            if is_combina_region:
                break
        if destination == "UPS":
            is_combina_region = False
        
        if is_combina_region:
            '''按组合柜计费'''
            return price
        
        return None

    except Exception as e:
        print(f"[_calculate_combina_price] 异常: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None


def _calculate_transfer_price(details: dict, fee_detail, warehouse: str, request: QuotationRequest) -> Optional[float]:
    """
    计算转运价格
    """
    try:
        target_warehouse = request.destination
        print(f'[_calculate_transfer_price] 开始计算转运价格 - 目标仓点: {target_warehouse}')
        print(f'[_calculate_transfer_price] details内容: {details}')
        
        if "LA" in warehouse and "LA_AMAZON" not in details:
            details = {"LA_AMAZON": details}
            print(f'[_calculate_transfer_price] 包装LA details')
        
        niche_warehouses = []
        if fee_detail['niche_warehouse']:
            niche_warehouses = fee_detail['niche_warehouse']
            print(f'[_calculate_transfer_price] 冷门仓点: {niche_warehouses}')
        
        is_niche = target_warehouse in niche_warehouses
        print(f'[_calculate_transfer_price] 是否冷门仓点: {is_niche}')
        
        print(f'[_calculate_transfer_price] 开始遍历details查找仓点')
        for category, zones in details.items():
            print(f'[_calculate_transfer_price] 分类: {category}')
            for zone, locations in zones.items():
                print(f'[_calculate_transfer_price] 区域: {zone}, 仓点列表: {locations}')
                if target_warehouse in locations:
                    try:
                        price = float(zone)
                        print(f'[_calculate_transfer_price] 找到匹配仓点，价格: {price}')
                        return price
                    except (ValueError, TypeError) as e:
                        print(f'[_calculate_transfer_price] 转换价格失败: {str(e)}')
                        continue
        
        print(f'[_calculate_transfer_price] 未找到目标仓点: {target_warehouse}')
        return None

    except Exception as e:
        print(f"[_calculate_transfer_price] 异常: {str(e)}")
        print(traceback.format_exc())
        return None
