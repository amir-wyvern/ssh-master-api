from typing import List, Union, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from enum import Enum
from datetime import datetime
import re
    

class HTTPError(BaseModel):

    message: str 
    internal_code: str

    class Config:
        schema_extra = {
            "example": {"detail": "HTTPException raised.", 'internal_code':1001},
        }
        
class UserRole(str ,Enum):

    CUSTOMER = 'CUSTOMER'
    AGENT = 'CUSTOMER'
    ADMIN = 'CUSTOMER'

class Status(int, Enum):

    DISABLE= 0
    ENABLE= 1

class ServerState(BaseModel):

    server_ip: str
    new_status: Status

class ServerCaps(BaseModel):

    server_ip: str
    new_caps: int

class NewServer(BaseModel):

    server_ip : str
    location: str
    ssh_port: int
    max_users: int
    ssh_accounts_number: int
    v2ray_accounts_number: int
    root_password: str
    manager_password: str
    status: Status


class ServerResponse(BaseModel):

    server_ip : str
    location: str
    ssh_port: int
    max_users: int
    ssh_accounts_number: int
    v2ray_accounts_number: int
    status: Status

    class Config:
        
        orm_mode= True


class NewSsh(BaseModel):

    interface_id : int
    tel_id: int

class NewSshResponse(BaseModel):

    username: str
    password: str
    host: str
    port: int


class UserInfo(BaseModel):

    tel_id: int


class DepositRequest(BaseModel):

    tel_id: int
    value: float

class DepositConfirmation(BaseModel):

    tel_id: int
    tx_hash: str


class RenewalSsh(BaseModel):

    service_id: int

class RenewalSshResponse(BaseModel):

    service_id: int
    expire: datetime

class DeleteSsh(BaseModel):

    username : str

class BlockSsh(BaseModel):

    username : str


class PhoneNumberStr(str):
    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any]) -> None:
        field_schema.update(type='string', format='phonenumber', example='+98-9151234567')

    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not re.match(r"^\+\d{1,3}-\d{6,12}$", v):
            raise ValueError("Not a valid phone number")
        return v

class UserRegisterForDataBase(BaseModel):

    tel_id: Optional[int] = None
    phone_number: Optional[PhoneNumberStr] = None
    email: Optional[EmailStr] = None
    role: UserRole

# class UserSShServiceDisplay(BaseModel):

#     service_id: int
#     server_ip: str
#     ssh_port: int
#     password: str
#     username: str

class ServiceType(str, Enum):

    SSH = 'SSH'
    V2RAY = 'V2RAY'


class UserSShServiceDisplay(BaseModel):

    service_id: int
    host: str
    port: int
    password: str
    username: str
    expire: datetime
    
class UserV2rayServiceDisplay(BaseModel):

    host: str
    id: str
    transport: str
    expire: datetime
    
class ServiceDisplay(BaseModel):

    service_type: ServiceType
    detail: Union[UserSShServiceDisplay, UserV2rayServiceDisplay]

class UserDisplay(BaseModel):

    user: UserRegisterForDataBase
    balance: float
    services: List[ServiceDisplay]

    class Config:
        orm_mode = True


class HTTPError(BaseModel):

    message: str 
    internal_code: str

    class Config:
        schema_extra = {
            "example": {"detail": "HTTPException raised.", 'internal_code':1001},
        }
        


class ServerRegister(BaseModel):

    server_ip: str
    root_password: str
    manager_password: str
    location: str
    ssh_port: int
    max_users: int
    ssh_accounts_number: int
    v2ray_accounts_number: int
    status: Status

class NewSshForDataBase(BaseModel):

    server_ip: str
    status: Status


class SshService(BaseModel):

    server_ip: str
    user_id: int
    interface_id: int
    port: int
    password: str
    username: str
    limit: int
    status: Status
    expire: datetime

class SshInterface(BaseModel):

    server_ip: str
    location: str
    port: int
    limit: int
    price: int
    traffic: int
    duration: int
    status: Status


class UserServiceRegister(BaseModel):

    ssh_service_id: int
    user_id: int


class PlanResponse(BaseModel):

    interface_id: int
    duration: int
    limit: int
    location: str
    price: int
    traffic: int

    class Config:
        orm_mode = True


class SshInterfaceRegister(BaseModel):

    server_ip: str
    location: str
    port: int
    limit: int
    price: int
    traffic: int
    duration: int
    status: Status

class SshInterfaceState(BaseModel):

    interface_id: int
    new_status: Status

class SshInterfaceResponse(BaseModel):

    interface_id: int


