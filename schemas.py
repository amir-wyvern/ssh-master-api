from typing import List, Union, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
from enum import Enum
from datetime import datetime
import re
    
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

class HTTPError(BaseModel):

    message: str 
    internal_code: str

    class Config:
        schema_extra = {
            "example": {"detail": "HTTPException raised.", 'internal_code':1001},
        }

class UserRole(str ,Enum):

    AGENT = 'agent'
    ADMIN = 'admin'

class Status(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'
    ALL= 'all'


class ChangeStatus(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'


class ServerState(BaseModel):

    server_ip: str

class FetchStatusServer(str, Enum):

    ALL = 'all'
    ONE = 'one'

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
    name: Optional[str] = None
    phone_number: Optional[PhoneNumberStr] = None
    email: Optional[EmailStr] = None
    chat_id: Optional[str] = None

class NewSshResponse(BaseModel):

    username: str
    password: str
    host: str
    port: int


class ServiceType(str, Enum):

    SSH = 'ssh'
    V2RAY = 'v2ray'


class UserInfo(BaseModel):

    tel_id: str


class DepositRequest(BaseModel):

    value: float

class SetNewBalance(BaseModel):

    username: str
    new_balance: Union[float, int]

class DepositConfirmation(BaseModel):

    tx_hash: str


class AgentBalanceResponse(BaseModel):

    balance: float


class UpdateSshExpire(BaseModel):

    username: str
    new_expire: datetime

class UpdateSshExpireResponse(BaseModel):

    username: str
    expire: datetime

class DeleteSsh(BaseModel):

    username : str

class BlockSsh(BaseModel):

    username : str

class UnBlockSsh(BaseModel):

    username : str

class UserRegister(BaseModel):

    tel_id: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[PhoneNumberStr] = None
    email: Optional[EmailStr] = None
    role: UserRole

class UserRegisterForDataBase(BaseModel):

    chat_id: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[PhoneNumberStr] = None
    email: Optional[EmailStr] = None
    bot_token: Optional[str] = None 
    username: str
    password: str
    status: Status
    role: UserRole


class AdminForDataBase(BaseModel):

    user_id: int
    bot_token: Optional[str]
    username: str
    password: str

class NewAgentForDataBase(BaseModel):

    user_id: int
    bot_token: Optional[str] = None
    username: str
    password: str
    status: Status


class AgentRequestForDataBase(BaseModel):

    user_id: int
    bot_token: str

# class UserSShServiceDisplay(BaseModel):

#     service_id: int
#     server_ip: str
#     ssh_port: int
#     password: str
#     username: str

class ServiceType(str, Enum):

    SSH = 'SSH'
    V2RAY = 'V2RAY'


class NewUserViaService(BaseModel):

    chat_id: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[PhoneNumberStr] = None
    email: Optional[EmailStr] = None
    agent_id: Optional[int] = None
    interface_id: int
    username: str
    password: str
    service_status: Status
    created: datetime
    expire: datetime

class UserSShServiceDisplay(BaseModel):

    service_id: int
    host: str
    port: int
    agent_id: int
    password: str
    username: str
    expire: datetime
    created: datetime
    
class UserV2rayServiceDisplay(BaseModel):

    host: str
    id: str
    transport: str
    expire: datetime
    
class ServiceDisplay(BaseModel):

    service_type: ServiceType
    detail: Union[UserSShServiceDisplay, UserV2rayServiceDisplay]

class UserServices(BaseModel):

    services: List[ServiceDisplay]

    class Config:
        orm_mode= True

class UserDisplay(BaseModel):

    user: UserRegisterForDataBase
    balance: float
    services: List[ServiceDisplay]

    class Config:
        orm_mode = True


class NewUserViaServiceResponse(BaseModel):

    service_id: int
    agent_id: int


class ChangeAgentStatus(BaseModel):

    username: str

class NewAgentRequest(BaseModel):

    chat_id: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[PhoneNumberStr] = None
    email: Optional[EmailStr] = None
    bot_token: Optional[str] = None
    username: str
    password: str
    status: Status


class AgentUpdateRequest(BaseModel):

    user_id: int
    bot_token: Optional[str]
    password: Optional[str]
    status: Optional[Status]

class UpdateAgentPassword(BaseModel):

    password: str

class UpdateAgentBotToken(BaseModel):

    bot_token: str


class UsersInfoAgent(BaseModel):

    number_day_to_expire: int
    status: Status


class UsersInfoAgentResponse(BaseModel):

    interface_id: int
    service_id: int
    server_ip: str
    agent_id: int
    username: str
    password: str
    name: Optional[str]
    phone_number: Optional[str]
    email: Optional[str]
    port: str
    status: Status
    created: datetime
    expire: datetime

    class Config:
        orm_mode= True

class AgentInfoResponse(BaseModel):

    agent_id: int
    chat_id: Optional[str]
    name: Optional[str]
    phone_number: Optional[str]
    email: Optional[str]
    bot_token: Optional[str]
    balance: float
    username: str
    total_user: int
    number_of_enable_services: int
    number_of_disable_services: int
    role: UserRole
    status: Status

class DepositRequestResponse(BaseModel):

    deposit_address: str
    request_id: str

class AgentListResponse(BaseModel):

    agent_id: int
    username: str
    total_user: int
    number_of_enable_users: int
    number_of_disable_users: int
    status: Status    

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
    agent_id: int
    user_chat_id: Optional[str]
    interface_id: int
    port: int
    password: str
    username: str
    name: Optional[str]
    phone_number: Optional[PhoneNumberStr]
    email: Optional[EmailStr]
    limit: int
    status: Status
    expire: datetime
    created: datetime


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

class InterfaceMode(str, Enum):

    ALL = 'all'
    BEST = 'best'

class PlanResponse(BaseModel):

    interface_id: int
    server_ip: str
    duration: int
    limit: int
    location: str
    price: int
    traffic: int
    status: Status

    class Config:
        orm_mode = True


class SshInterfaceRegister(BaseModel):

    server_ip: str
    location: str
    port: int
    limit: int
    price: float
    traffic: int
    duration: int
    status: Status

class SshInterfaceState(BaseModel):

    interface_id: int

class SshInterfaceResponse(BaseModel):

    interface_id: int
    status: Status


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: int | None = None
    role: UserRole | None = None
    scopes: list[str] = []

class TokenUser(BaseModel):

    user_id: int
    role: UserRole
