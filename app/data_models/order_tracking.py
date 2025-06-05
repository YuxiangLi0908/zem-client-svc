from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OrderTrackingRequest(BaseModel):
    container_number: str


class UserResponse(BaseModel):
    zem_name: str
    full_name: str
    zem_code: str
    email: Optional[str]
    note: Optional[str]
    phone: Optional[str]
    accounting_name: Optional[str]
    address: Optional[str]
    username: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class ContainerResponse(BaseModel):
    container_number: str
    container_type: Optional[str]
    weight_lbs: Optional[float]
    is_special_container: Optional[bool]
    note: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class WarehouseResponse(BaseModel):
    name: str
    address: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class VesselResponse(BaseModel):
    vessel_id: Optional[str]
    master_bill_of_lading: Optional[str]
    origin_port: Optional[str]
    destination_port: Optional[str]
    shipping_line: Optional[str]
    vessel: Optional[str]
    voyage: Optional[str]
    vessel_etd: Optional[date]
    vessel_eta: Optional[date]

    model_config = ConfigDict(from_attributes=True)


class RetrievalResponse(BaseModel):
    retrieval_id: Optional[str]
    shipping_order_number: Optional[str]
    master_bill_of_lading: Optional[str]
    retrive_by_zem: Optional[bool]
    retrieval_carrier: Optional[str]
    origin_port: Optional[str]
    destination_port: Optional[str]
    shipping_line: Optional[str]
    retrieval_destination_precise: Optional[str]
    assigned_by_appt: Optional[bool]
    retrieval_destination_area: Optional[str]
    scheduled_at: Optional[datetime]
    target_retrieval_timestamp: Optional[datetime]
    target_retrieval_timestamp_lower: Optional[datetime]
    actual_retrieval_timestamp: Optional[datetime]
    note: Optional[str]
    arrive_at_destination: Optional[bool]
    arrive_at: Optional[datetime]
    empty_returned: Optional[bool]
    empty_returned_at: Optional[datetime]
    temp_t49_lfd: Optional[date]
    temp_t49_available_for_pickup: Optional[bool]
    temp_t49_pod_arrive_at: Optional[datetime]
    temp_t49_pod_discharge_at: Optional[datetime]
    temp_t49_hold_status: Optional[bool]

    model_config = ConfigDict(from_attributes=True)


class OffloadResponse(BaseModel):
    offload_id: Optional[str]
    offload_required: Optional[bool]
    offload_at: Optional[datetime]
    total_pallet: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class OrderPreportResponse(BaseModel):
    order_id: Optional[str]
    created_at: datetime
    eta: Optional[date]
    order_type: Optional[str]
    customer_do_link: Optional[str]
    do_sent: Optional[bool]
    add_to_t49: Optional[bool]
    packing_list_updloaded: Optional[bool]
    cancel_notification: Optional[bool]
    cancel_time: Optional[date]
    user: Optional[UserResponse]
    container: Optional[ContainerResponse]
    warehouse: Optional[WarehouseResponse]
    vessel: Optional[VesselResponse]
    retrieval: Optional[RetrievalResponse]
    offload: Optional[OffloadResponse]

    model_config = ConfigDict(from_attributes=True)



class OrderPostportResponse(BaseModel):
    order_id: Optional[str]

    model_config = ConfigDict(from_attributes=True)



class OrderResponse(BaseModel):
    preport_timenode: Optional[OrderPreportResponse]
    postport_timenode: Optional[OrderPostportResponse]