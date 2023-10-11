from typing import List, Union, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field
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


class Status(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'
    DELETED= 'deleted'
    NONE= 'none'


class ServiceStatusDb(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'
    EXPIRED= 'expired'
    DELETED= 'deleted'

class ConfigType(str, Enum):

    MAIN= 'main'
    TEST= 'test'

class UserStatusDb(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'

class UserStatusWithNone(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'
    NONE= 'none'



# ============= Server =============

class ServerStatusDb(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'

class ServerStatusWithNone(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'
    NONE= 'none'

class DeployStatus(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'

class ServerType(str, Enum):

    MAIN= 'main'
    PROXY= 'proxy'

class FetchStatusServer(str, Enum):

    ALL = 'all'
    ONE = 'one'

class ServerRegister(BaseModel):

    server_ip: str
    root_password: str
    manager_password: str
    location: str
    ssh_port: int
    max_users: int
    ssh_accounts_number: int
    v2ray_accounts_number: int
    server_type: ServerType
    generate_status: ServerStatusDb
    update_expire_status: ServerStatusDb
    status: ServerStatusDb

class UpdateServerStatus(BaseModel):

    server_ip: str
    new_generate_status: Optional[ServerStatusDb]    
    new_update_expire_status: Optional[ServerStatusDb]    
    new_status: Optional[ServerStatusDb]    

class ServerConnection(str, Enum):

    CONNECTED= 'connected'
    DISCONNECT= 'disconnect'

class NodesStatusDetail(BaseModel):

    ip: str
    status: ServerStatusDb
    connection: ServerConnection

class NodesStatusResponse(BaseModel):

    count: int
    detail: List[NodesStatusDetail]

class BestServerForNewConfig(BaseModel):

    server_ip: str
    ssh_port: int
    ssh_accounts_number: int
    max_users: int

class UsersResponse(BaseModel):

    count: int
    result: List[str]

class UpdateMaxUserServer(BaseModel):
    
    server_ip: str
    new_max_user: int = Field(gt=0)

class ActiveUsersDetail(BaseModel):

    ip: str
    detail: List[Dict]
    active_sessions: int
    active_users: int
    
class ActiveUsersResponse(BaseModel):

    server_number: int
    total_active_users: int
    total_sessions: int
    detail: List[ActiveUsersDetail]
    
class ServerCaps(BaseModel):

    server_ip: str
    new_caps: int

class NewServerResponse(BaseModel):

    server_ip: str
    domain_name: str

class NewServer(BaseModel):

    server_ip : str
    server_type: ServerType
    location: str
    ssh_port: int
    max_users: int
    ssh_accounts_number: int
    v2ray_accounts_number: int
    root_password: str
    manager_password: str
    generate_status: ServerStatusDb
    update_expire_status: ServerStatusDb
    status: ServerStatusDb

class ServerResponse(BaseModel):

    server_ip : str
    location: str
    ssh_port: int
    max_users: int
    root_password: str
    manager_password: str
    ssh_accounts_number: int
    v2ray_accounts_number: int
    server_type: ServerType
    generate_status: ServerStatusDb
    update_expire_status: ServerStatusDb
    status: ServerStatusDb

    class Config:
        
        orm_mode= True

class FetchServerResponse(BaseModel):

    count: int
    result: List[ServerResponse]

class UpdateNodesResponse(BaseModel):

    message: str
    errors : List[Dict[str,str]]

class ServerTransfer(BaseModel):

    old_server_ip: str
    new_server_ip: str
    disable_old_server: bool
    delete_old_users: bool

class ServerTransferResponse(BaseModel):

    from_server: str
    to_server: str
    domains_updated: List[str]
    success_users: List[str]
    create_exists_users: List[str]
    block_not_exists_users: List[str]
    delete_not_exists_users: List[str]


# ============= Domain =============

class DomainStatusDb(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'

class DomainStatusWithNone(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'
    NONE= 'none'

class DomainRegister(BaseModel):

    domain_name: str
    server_ip: str
    status: DomainStatusDb

class DomainRegisterForDb(BaseModel):

    domain_name: str
    identifier: str
    server_ip: str
    status: DomainStatusDb

class NewDomainResponse(BaseModel):

    domain_id: int
    identifier: str
    domain_name: str
    server_ip: str
    status: DomainStatusDb

    class Config:
        orm_mode = True

class UpdateDomainStatus(BaseModel):

    domain_name: str
    new_status: DomainStatusDb

class UpdateServerInDomain(BaseModel):

    domain_name: str
    server_ip: str

class UpdateServerInDomainResponse(BaseModel):

    domain_id : int
    domain_name: str
    server_ip: str
    status: DomainStatusDb

    class Config:
        orm_mode = True

class DomainResponse(BaseModel):

    domain_id: int
    domain_name: str
    identifier: str
    server_ip: str
    status: DomainStatusDb

    class Config:
        orm_mode= True

class FetchDomainResponse(BaseModel):

    count: int
    result: List[DomainResponse]


# ============= Ssh =============

class UpdateSshExpire(BaseModel):

    username: str
    new_expire: datetime
    unblock: bool = True

class UpdateSshExpireResponse(BaseModel):

    username: str
    expire: datetime
    unblock: bool = True

class DeleteSsh(BaseModel):

    username : str

class RenewSsh(BaseModel):

    username : str
    new_domain_name: Optional[str]

class BlockSsh(BaseModel):

    username : str

class UnBlockSsh(BaseModel):

    username : str

class NewSsh(BaseModel):

    plan_id : int
    domain_name: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[PhoneNumberStr] = None
    email: Optional[EmailStr] = None
    chat_id: Optional[str] = None

class NewSshResponse(BaseModel):

    username: str
    password: str
    host: str
    port: int

class NewSshForDataBase(BaseModel):

    server_ip: str
    status: Status

class SshService(BaseModel):

    service_type: ConfigType
    agent_id: int
    user_chat_id: Optional[str]
    plan_id: int
    domain_id: int
    password: str
    username: str
    name: Optional[str]
    phone_number: Optional[PhoneNumberStr]
    email: Optional[EmailStr]
    status: ServiceStatusDb
    expire: datetime
    created: datetime

class DomainTransfer(BaseModel):

    old_domain_name: str
    new_domain_name: Optional[str]
    new_server_ip: Optional[str]
    disable_old_domain: bool
    delete_old_users: bool

class DomainTransferResponse(BaseModel):

    old_domain_name: str
    new_domain_name: Optional[str]
    from_server: str
    to_server: str
    success_users: List[str]
    create_exists_users: List[str]
    block_not_exists_users: List[str]
    delete_not_exists_users: List[str]

class NewUserViaSshService(BaseModel):

    chat_id: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[PhoneNumberStr] = None
    email: Optional[EmailStr] = None
    agent_id: Optional[int] = None
    plan_id: int
    username: str
    password: str
    service_status: Status
    created: datetime
    expire: datetime

class UserSShServiceDisplay(BaseModel):

    service_id: int
    service_type: ConfigType
    domain_id: int
    domain_name: str
    server_ip: str
    ssh_port: int
    plan_id: int
    name: Optional[str]
    email: Optional[EmailStr]
    phone_number: Optional[PhoneNumberStr]
    agent_id: int
    password: str
    username: str
    created: datetime
    expire: datetime
    status: ServiceStatusDb

    class Config:
        orm_mode= True

class SearchResponse(BaseModel):

    count: int
    result: List[UserSShServiceDisplay] 

# ============= V2ray =============

class UserV2rayServiceDisplay(BaseModel):

    service_id: int



# ============= Service =============

class ServiceType(str, Enum):

    SSH = 'ssh'
    V2RAY = 'v2ray'


class ServiceDisplay(BaseModel):

    service_type: ServiceType
    detail: Union[UserSShServiceDisplay, UserV2rayServiceDisplay]

class UserServices(BaseModel):

    services: List[ServiceDisplay]

    class Config:
        orm_mode= True



# ============= User =============

class UserFinancial(BaseModel):

    user_id: int
    username: str
    password: str = None

class UserInfo(BaseModel):

    tel_id: str

class UserAgentStatus(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'
    ALL= 'all'

class UserRole(str ,Enum):

    AGENT = 'agent'
    ADMIN = 'admin'

class UserRegisterForDataBase(BaseModel):

    chat_id: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[PhoneNumberStr] = None
    email: Optional[EmailStr] = None
    bot_token: Optional[str] = None 
    username: str
    password: str
    status: UserStatusDb
    referal_link: str
    parent_agent_id: int
    subset_limit: int
    role: UserRole

class UserDisplay(BaseModel):

    user: UserRegisterForDataBase
    balance: float
    services: List[ServiceDisplay]

    class Config:
        orm_mode = True

class UserServiceRegister(BaseModel):

    ssh_service_id: int
    user_id: int

class UsersInfoAgent(BaseModel):

    number_day_to_expire: int
    status: Status

class UsersInfoAgentResponse(BaseModel):

    service_id: int
    service_type: ConfigType
    plan_id: int
    domain_id: str
    agent_id: int
    username: str
    password: str
    name: Optional[str]
    phone_number: Optional[str]
    email: Optional[str]
    status: ServiceStatusDb
    created: datetime
    expire: datetime

    class Config:
        orm_mode= True

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

class NewUserViaSshServiceResponse(BaseModel):

    service_id: int
    agent_id: int

class ChangeAgentStatus(BaseModel):

    username: str
    new_status: UserStatusDb

class NewAgentRequest(BaseModel):

    chat_id: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[PhoneNumberStr] = None
    email: Optional[EmailStr] = None
    bot_token: Optional[str] = None
    username: str
    password: str
    subset_limit: Optional[int] = 5
    referal_link: Optional[str]
    status: UserStatusDb

class NewAgentResponse(BaseModel):

    agent_id: int
    referal_link: str

class AgentUpdateRequest(BaseModel):

    user_id: int
    bot_token: Optional[str]
    password: Optional[str]
    status: Optional[Status]

class UpdateAgentPassword(BaseModel):

    password: str

class PaymentMeothodPartnerShip(str, Enum):

    WALLET = 'wallet'
    WITHDRAW = 'withdraw'

class ClaimPartnerShipProfit(BaseModel):

    value: float
    method: PaymentMeothodPartnerShip

class UpdateAgentBotToken(BaseModel):

    bot_token: str

class UpdateAgentChatID(BaseModel):

    new_chat_id: str

class AgentInfoResponse(BaseModel):

    agent_id: int
    parent_agent_id: int
    chat_id: Optional[str]
    name: Optional[str]
    phone_number: Optional[str]
    email: Optional[str]
    bot_token: Optional[str]
    balance: float
    username: str
    subset_not_released_profit: float
    subset_total_profit: float
    subset_number_of_configs: int
    subset_number_limit: int
    total_user: int
    enable_ssh_services: int
    disable_ssh_services: int
    expired_ssh_services: int
    deleted_ssh_services: int
    test_ssh_services: int
    referal_link: str
    parent_agent_id: int
    role: UserRole
    subset_list: List[str]
    status: UserStatusDb

class AgentListResponse(BaseModel):

    agent_id: int
    parent_agent_id: int
    username: str
    subset_not_released_profit: float
    subset_total_profit: float
    subset_number_of_configs: int
    subset_limit: int
    number_of_subsets: int
    balance: float
    total_ssh_user: int
    enable_ssh_services: int
    disable_ssh_services: int
    expired_ssh_services: int
    deleted_ssh_services: int
    referal_link: str
    status: UserStatusDb

class FetchAgentListResponse(BaseModel):

    count: int
    result: List[AgentListResponse]

class ListSubsetResponse(BaseModel):

    user_id: int
    username: str
    name: Union[str, None]
    status: UserStatusDb

    class Config:
        orm_mode = True

class UpdateSubsetLimit(BaseModel):

    username: str
    new_limit: int


# ============= Plan =============

class SshPlan(BaseModel):

    limit: int
    price: int
    traffic: int
    duration: int
    status: Status

class PlanStatusDb(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'

class PlanStatusWithNone(str, Enum):

    DISABLE= 'disable'
    ENABLE= 'enable'
    NONE= 'none'

class PlanMode(str, Enum):

    ALL = 'all'
    BEST = 'best'

class PlanResponse(BaseModel):

    plan_id: int
    duration: int
    limit: int
    price: int
    traffic: int
    status: PlanStatusDb

    class Config:
        orm_mode = True

class FetchPlanResponse(BaseModel):

    count: int
    result: List[PlanResponse]

class SshPlanRegister(BaseModel):

    limit: int
    price: float
    traffic: int
    duration: int
    status: PlanStatusDb

class SshPlanState(BaseModel):

    plan_id: int
    new_status: PlanStatusDb

class SshPlanResponse(BaseModel):

    plan_id: int
    status: PlanStatusDb

class NewSshPlanResponse(BaseModel):

    plan_id: int

class UsersTransferToNewPlan(BaseModel):

    old_intface_id: int
    new_interface_id: int
    delete_old_users: bool = False



# ============= Financial =============

class DepositRequest(BaseModel):

    value: float

class DepositConfirmation(BaseModel):

    tx_hash: str

class DepositRequestResponse(BaseModel):

    deposit_address: str
    request_id: str

class SetNewBalance(BaseModel):

    username: str
    value: Union[float, int]

class NewBalanceResponse(BaseModel):

    username: str
    current_balance: Union[float, int]

class AgentBalanceResponse(BaseModel):

    balance: float


# ============= Token =============
#  
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: int | None = None
    role: UserRole | None = None
    scopes: List[str] = []

class TokenUser(BaseModel):

    user_id: int
    role: UserRole


# ============= Subset =============

class CreateSubsetProfit(BaseModel):

    user_id : int
    not_released_profit: float
    total_profit: float
    number_of_configs: int



# ================ Notification ================

class NotificationStatus(str, Enum):

    SUCCESSFULL= 'successfull'
    FAILED= 'failed'

class PublishNotification(BaseModel):

    message: str
    parse_mode: bool = False
    except_agents: Optional[List[str]]
    accept_agents: Optional[List[str]]

class PublishNotificationResponse(BaseModel):

    status: NotificationStatus
    failed_users: List[str]
