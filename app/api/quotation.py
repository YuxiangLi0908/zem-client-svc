from datetime import date, datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text, or_, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel
import traceback
import os
import aiohttp

from app.services.db_session import db_session
from app.services.user_auth import get_current_user
from app.data_models.db.user import User
from app.data_models.db.quotation_master import QuotationMaster
from app.data_models.db.fee_detail import FeeDetail
from app.data_models.db.maersk_price_rate import MaerskPriceRate

router = APIRouter()


class QuotationRequest(BaseModel):
    destination: str
    cbm: Optional[float] = None
    pallets: Optional[int] = None
    container_type: str


class QuotationItem(BaseModel):
    warehouse: str
    type: str
    price: Optional[float] = None
    message: Optional[str] = None
    unit_price: Optional[float] = None
    pallets: Optional[float] = None


class QuotationResponse(BaseModel):
    effective_date: Optional[date] = None
    quotations: list[QuotationItem]
    show_maersk: bool = False


class MaerskLineItem(BaseModel):
    description: str
    pieces: int
    length: int
    width: int
    height: int
    weight: int


class MaerskQuotationRequest(BaseModel):
    warehouse: str
    dest_zip: str
    ship_date: str
    need_liftgate: str
    items: List[MaerskLineItem]


class MaerskQuotationResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


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
        if request.cbm is None and request.pallets is None:
            raise HTTPException(status_code=400, detail="CBM和板数必须至少填写一个")
        
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
                price_result = None
                message = None

                try:
                    uppercase_request = QuotationRequest(
                        destination=request.destination.upper(),
                        cbm=request.cbm,
                        pallets=request.pallets,
                        container_type=request.container_type
                    )
                    
                    price_result = _get_quotation_price(
                        db=db,
                        quotation_master=quotation_master,
                        warehouse=warehouse,
                        quote_type=quote_type,
                        request=uppercase_request
                    )

                    if price_result is not None:
                        
                        quotation_item = QuotationItem(
                            warehouse=warehouse,
                            type=quote_type,
                            price=price_result.get('price'),
                            message=None
                        )
                        if 'unit_price' in price_result:
                            quotation_item.unit_price = price_result['unit_price']
                        if 'pallets' in price_result:
                            quotation_item.pallets = price_result['pallets']
                        results.append(quotation_item)
                    else:
                        message = "没有报价"

                except Exception as e:
                    db.rollback()
                    message = f"查询失败: {str(e)}"
                    print(traceback.format_exc())

        print('\n[query_quotation] ===== 询价完成 =====')
        show_maersk = len(results) == 0
        
        return QuotationResponse(
            effective_date=quotation_master.get('effective_date'),
            quotations=results,
            show_maersk=show_maersk
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
) -> Optional[dict]:
    """
    获取报价价格
    """
    try:
        
        fee_detail = _get_fee_detail(db, quotation_master['id'], warehouse, quote_type)
        if not fee_detail:
            return None

        # 查找cbm除以的比例
        cbm_per_pl_default = 2.2
        try:
            details = fee_detail.get('details', {})
            if details and 'global_rules' in details:
                global_rules = details['global_rules']
                if 'cbm_per_pl' in global_rules:
                    cbm_per_pl = global_rules['cbm_per_pl']
                    if 'default' in cbm_per_pl:
                        cbm_per_pl_default = cbm_per_pl['default']
        except Exception as e:
            print(f'[_get_quotation_price] 提取cbm_per_pl_default失败: {e}')
        
        price_result = _calculate_price(fee_detail, quote_type, warehouse, request, cbm_per_pl_default)
        return price_result

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


def _calculate_price(fee_detail, quote_type: str, warehouse: str, request: QuotationRequest, cbm_per_pl_default) -> Optional[dict]:
    """
    计算价格
    """
    try:
        
        if not fee_detail or not fee_detail['details']:
            return None

        details = fee_detail.get('details')
        
        if quote_type == "组合柜":
            price = _calculate_combina_price(details, request)
            if price is not None:
                return {'price': price}
            return None
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


def _calculate_transfer_price(details: dict, fee_detail, warehouse: str, request: QuotationRequest, cbm_per_pl_default) -> Optional[dict]:
    """
    计算转运价格
    """
    try:
        target_warehouse = request.destination.upper()
        
        if "LA" in warehouse and "LA_AMAZON" not in details:
            details = {"LA_AMAZON": details}
        
        niche_warehouses = []
        if fee_detail['niche_warehouse']:
            niche_warehouses = fee_detail['niche_warehouse']
        
        is_niche = target_warehouse in niche_warehouses
        pallets = request.pallets
        cbm = request.cbm
        
        must_pallet = None
        actual_plt = None

        if cbm:
            raw_p = cbm / float(cbm_per_pl_default)
            must_pallet = _calculate_total_pallet(raw_p, is_niche, warehouse)
        
        if cbm and not pallets:
            actual_plt = must_pallet
        elif pallets and not cbm:
            actual_plt = pallets
        elif cbm and pallets:
            actual_plt = max(must_pallet, pallets)
        
        if actual_plt is None:
            return None
        
        for category, zones in details.items():
            for zone, locations in zones.items():
                if target_warehouse in locations:
                    try:
                        unit_price = float(zone)
                        price = unit_price * actual_plt
                        return {
                            'price': price,
                            'unit_price': unit_price,
                            'pallets': actual_plt
                        }
                    except (ValueError, TypeError) as e:
                        continue
        return None

    except Exception as e:
        print(traceback.format_exc())
        return None

def _calculate_total_pallet(raw_p: float, is_niche_warehouse: bool, warehouse: str) -> float:
    '''板数计算公式'''
    integer_part = int(raw_p)
    decimal_part = raw_p - integer_part

    # 尚未启用的新规则
    is_new_rule = False
    # 本地派送的按照4.1之前的规则
    if decimal_part > 0:
        if is_new_rule:
            # 按照LA和NJSAV不同规则去计算
            if warehouse in ['NJ', 'SAV']:
                # NJ 或 SAV 仓库
                if is_niche_warehouse:
                    # 冷门仓点
                    if decimal_part > 0.5:
                        additional = 1  # 超过0.5进位整板
                    else:
                        additional = 0.5  # 不超过0.5按0.5板计费
                else:
                    # 热门仓点
                    additional = 1 if decimal_part > 0.5 else 0  # 超过0.5进位整板，否则减免
                
            elif warehouse == 'LA':
                # LA 仓库
                if is_niche_warehouse:
                    # 冷门仓点：小数点不足一个板，按照1个板计算
                    additional = 1 if decimal_part > 0 else 0
                else:
                    # 热门仓点
                    if decimal_part > 0.9:
                        additional = 1  # 0.9以上按1个板
                    else:
                        additional = 0.5  # 0.1-0.9按0.5个板
        else:  # etd4.1之后的
            if is_niche_warehouse:
                additional = 1 if decimal_part > 0.5 else 0.5
            else:
                additional = 1 if decimal_part > 0.5 else 0
        total_pallet = integer_part + additional
    elif decimal_part == 0:
        total_pallet = integer_part
    else:
        raise ValueError("板数计算错误")
    return total_pallet


def get_maersk_increase_percentage(db: Session, current_user: User) -> float:
    """
    获取当前用户适用的Maersk涨价百分比
    """
    try:
        username = current_user.username
        
        # 先找用户专属的记录，按生效日期降序
        user_exclusive = db.query(MaerskPriceRate).filter(
            MaerskPriceRate.is_user_exclusive == True,
            MaerskPriceRate.exclusive_user == username
        ).order_by(desc(MaerskPriceRate.effective_date)).first()
        print('user_exclusive',user_exclusive)
        if user_exclusive:
            return user_exclusive.increase_percentage
        
        # 找不到则找非用户专属的记录，按生效日期降序
        general = db.query(MaerskPriceRate).filter(
            MaerskPriceRate.is_user_exclusive == False
        ).order_by(desc(MaerskPriceRate.effective_date)).first()
        print('general',general)
        if general:
            return general.increase_percentage
        
        # 如果都没有找到，默认不涨价
        return 1.0
    except Exception as e:
        print(f"获取涨价百分比失败: {e}")
        return 1.0


@router.post("/maersk_quotation", response_model=MaerskQuotationResponse)
async def maersk_quotation(
    request: MaerskQuotationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session.get_db),
) -> MaerskQuotationResponse:
    """
    Maersk询价API
    """
    try:
        zip_map = {
            'NJ': '07001',
            'SAV': '31326',
            'LA': '91761'
        }
        origin_zip = zip_map.get(request.warehouse)
        if not origin_zip:
            return MaerskQuotationResponse(
                success=False,
                message=f'无效的仓库代码: {request.warehouse}'
            )
        
        dest_zip = request.dest_zip.strip()
        ship_date = request.ship_date
        need_liftgate = 'true' if str(request.need_liftgate).strip() in ('是', 'true', 'True', '1') else 'false'
        
        if not all([origin_zip, dest_zip, ship_date]):
            return MaerskQuotationResponse(
                success=False,
                message='基础参数不完整'
            )
        
        line_items = []
        for item in request.items:
            line_items.append({
                "description": item.description or 'Pallet',
                "pieces": item.pieces,
                "length": item.length,
                "width": item.width,
                "height": item.height,
                "weight": item.weight
            })
        
        ship_date_formatted = ship_date
        try:
            if ship_date and '-' in ship_date:
                parts = ship_date.split('-')
                if len(parts) == 3:
                    ship_date_formatted = f"{parts[1].zfill(2)}/{parts[2].zfill(2)}/{parts[0]}"
        except Exception:
            ship_date_formatted = ship_date
        
        rating_items = [
            {
                "description": it["description"],
                "pieces": it["pieces"],
                "length": it["length"],
                "width": it["width"],
                "height": it["height"],
                "weight": it["weight"],
            }
            for it in line_items
        ]
        
        payload = {
            "shipDate": ship_date_formatted,
            "origin_zip": origin_zip,
            "dest_zip": dest_zip,
            "lineItems": rating_items,
            "liftgate": need_liftgate,
            "declaredValue": None,
            "insuranceValue": None,
            "debrisRemoval": None
        }
        api_url = "https://zem-maersk-gateway.kindmoss-a5050a64.eastus.azurecontainerapps.io/rating"
        api_key = os.environ.get("MAERSK_API_KEY")
        
        if not api_key:
            return MaerskQuotationResponse(
                success=False,
                message='未配置API Key'
            )
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    data['lineItems'] = line_items
                    data['need_liftgate'] = need_liftgate
                    
                    increase_percentage = get_maersk_increase_percentage(db, current_user)
                    print(f"涨价百分比: {increase_percentage}")
                    
                    if 'quotes' in data:
                        for quote in data['quotes']:
                            if 'TotalQuote' in quote and quote['TotalQuote'] is not None:
                                quote['TotalQuote'] = round(quote['TotalQuote'] * increase_percentage, 2)
                            
                            if 'Charges' in quote:
                                for charge in quote['Charges']:
                                    if 'Amount' in charge and charge['Amount'] is not None:
                                        charge['Amount'] = round(charge['Amount'] * increase_percentage, 2)
                    
                    return MaerskQuotationResponse(
                        success=True,
                        data=data
                    )
                else:
                    text = await response.text()
                    
                    error_message = f'API调用失败: {response.status} - {text}'
                    
                    if 'Unable to find the scale' in text:
                        error_message = '暂无该地址的报价'
                    elif 'Unable to find' in text:
                        error_message = '暂无该地址的报价'
                    
                    return MaerskQuotationResponse(
                        success=False,
                        message=error_message
                    )
    
    except Exception as e:
        print(traceback.format_exc())
        return MaerskQuotationResponse(
            success=False,
            message=str(e)
        )