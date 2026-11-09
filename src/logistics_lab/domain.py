from typing import Literal, get_args

RequestType = Literal["mail_parcel", "dispatch", "driver_booking", "warehouse_order"]
Category = Literal["mail_parcel", "dispatch", "driver_booking", "warehouse_order", "other"]

REQUEST_TYPES = get_args(RequestType)
CATEGORIES = get_args(Category)
PRIORITIES = ("low", "normal", "high", "urgent")
