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
    effective_date: Optional[date] = None
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
        warehouses = ["NJ", "SAV", "LA"]
        quotation_types = ["转运", "组合柜"]
        results = []

        vessel_etd = date.today()
        customer_name = current_user.username
        

        db.rollback()
        
        quotation_master = _get_quotation_master(db, customer_name, vessel_etd)
        if not quotation_master:
            for warehouse in warehouses:
                for quote_type in quotation_types:
                    results.append(QuotationItem(
                        warehouse=warehouse,
                        type=quote_type,
                        price=None,
                        message="没有报价"
                    ))
            return QuotationResponse(quotations=results)

        for warehouse in warehouses:
            for quote_type in quotation_types:
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
                        
                        results.append(QuotationItem(
                            warehouse=warehouse,
                            type=quote_type,
                            price=price,
                            message=None
                        ))
                    else:
                        message = "没有报价"

                except Exception as e:
                    db.rollback()
                    message = f"查询失败: {str(e)}"
                    print(traceback.format_exc())

        print('\n[query_quotation] ===== 询价完成 =====')
        return QuotationResponse(
            effective_date=quotation_master.get('effective_date'),
            quotations=results
        )

    except Exception as e:
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
        
        fee_detail = _get_fee_detail(db, quotation_master['id'], warehouse, quote_type)
        if not fee_detail:
            return None

        # 查找cbm除以的比例
        query = text("""
            SELECT id, details, niche_warehouse,
                JSON_EXTRACT(details, '$.global_rules.cbm_per_pl.default') AS cbm_per_pl_default
            FROM warehouse_feeDetail
            WHERE quotation_id_id = :quotation_id
            AND fee_type = :fee_type
            LIMIT 1
        """)
        result = db.execute(query, {
            'quotation_id': quotation_master['id'],
            'fee_type': 'COMBINA_STIPULATE'
        }).fetchone()

        if result:
            # 方式1：直接使用查询中提取的字段
            cbm_per_pl_default = result.cbm_per_pl_default
        price = _calculate_price(fee_detail, quote_type, warehouse, request, cbm_per_pl_default)
        return price

    except Exception as e:
        print(traceback.format_exc())
        return None


def _get_quotation_master(db: Session, customer_name: str, vessel_etd: date):
    """
    获取报价表
    """
    try:
        db.rollback()
        
        query = text("""
            SELECT id, filename, effective_date
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
            query = text("""
                SELECT id, filename, effective_date
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
            return {'id': result[0], 'filename': result[1], 'effective_date': result[2]}
        else:
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
            #if result[1]:
                #print(f'[_get_fee_detail] 有details数据')
            #if result[2]:
                #print(f'[_get_fee_detail] 有niche_warehouse数据')
            return {'id': result[0], 'details': result[1], 'niche_warehouse': result[2]}
        else:
            print(f'[_get_fee_detail] 未找到费用明细 - 报价ID: {quotation_id}, 费用类型: {fee_type}')
            return None

    except Exception as e:
        print(traceback.format_exc())
        db.rollback()
        return None


def _calculate_price(fee_detail, quote_type: str, warehouse: str, request: QuotationRequest, cbm_per_pl_default) -> Optional[float]:
    """
    计算价格
    """
    try:
        
        if not fee_detail or not fee_detail['details']:
            return None

        details = fee_detail.get('details')
        
        if quote_type == "组合柜":
            return _calculate_combina_price(details, request)
        else:
            return _calculate_transfer_price(details, fee_detail, warehouse, request, cbm_per_pl_default)

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
        import traceback
        print(traceback.format_exc())
        return None


def _calculate_transfer_price(details: dict, fee_detail, warehouse: str, request: QuotationRequest, cbm_per_pl_default) -> Optional[float]:
    """
    计算转运价格
    """
    try:
        target_warehouse = request.destination
        
        if "LA" in warehouse and "LA_AMAZON" not in details:
            details = {"LA_AMAZON": details}
        
        niche_warehouses = []
        if fee_detail['niche_warehouse']:
            niche_warehouses = fee_detail['niche_warehouse']
        
        is_niche = target_warehouse in niche_warehouses
        pallets = request.pallets
        cbm = request.cbm
        if cbm and pallets:
            actual_plt = max( cbm / float(cbm_per_pl_default), pallets)
        elif cbm:
            actual_plt = cbm / float(cbm_per_pl_default)
        elif pallets:
            actual_plt = pallets
        
        
        for category, zones in details.items():
            for zone, locations in zones.items():
                if target_warehouse in locations:
                    try:
                        price = float(zone) * actual_plt
                        return price
                    except (ValueError, TypeError) as e:
                        continue
        return None

    except Exception as e:
        print(traceback.format_exc())
        return None
