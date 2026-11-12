from dataclasses import dataclass, field


@dataclass
class KnowledgeIntent:
    """知识意图：说明含义并绑定负责提供知识的 Provider"""

    id: str          # 意图唯一标识，例如 hotel_info
    description: str  # 自然语言说明，供 Planning 理解
    provider_ids: list[str] = field(default_factory=list)
    requires_object: str | None = None  # 依赖的对象类型，无依赖时为 None


# 意图与 Provider 的映射
KNOWLEDGE_INTENTS: dict[str, KnowledgeIntent] = {
    # ---------- 产品咨询（依赖用户选中的对象） ----------
    "hotel_info": KnowledgeIntent(
        id="hotel_info",
        description="酒店信息咨询，例如酒店设施、星级、地址、入住退房时间",
        provider_ids=["api.hotel"],
        requires_object="hotel",
    ),
    "scenic_info": KnowledgeIntent(
        id="scenic_info",
        description="景点信息咨询，例如景点介绍、开放时间、等级、票种",
        provider_ids=["api.scenic"],
        requires_object="scenic",
    ),
    "flight_info": KnowledgeIntent(
        id="flight_info",
        description="航班信息咨询，例如航班号、起降时间、舱位与行李额",
        provider_ids=["api.flight"],
        requires_object="flight",
    ),
    "train_info": KnowledgeIntent(
        id="train_info",
        description="车次信息咨询，例如车次号、起终站、发到时间、席位",
        provider_ids=["api.train"],
        requires_object="train",
    ),
    "bus_info": KnowledgeIntent(
        id="bus_info",
        description="班次信息咨询，例如班线、发车时间、票价与余座",
        provider_ids=["api.bus"],
        requires_object="bus",
    ),
    "transfer_info": KnowledgeIntent(
        id="transfer_info",
        description="接送服务咨询，例如服务类型、车型、载客人数",
        provider_ids=["api.transfer"],
        requires_object="transfer",
    ),
    # ---------- 订单与售后 ----------
    "order_info": KnowledgeIntent(
        id="order_info",
        description="订单信息咨询，例如订单状态、金额、预订产品",
        provider_ids=["api.order"],
        requires_object="order",
    ),
    "payment_info": KnowledgeIntent(
        id="payment_info",
        description="订单支付信息咨询，例如支付方式、支付状态、支付时间",
        provider_ids=["api.payment"],
        requires_object="order",
    ),
    "refund_status": KnowledgeIntent(
        id="refund_status",
        description="退款进度咨询，例如退款申请状态、退款金额、到账情况",
        provider_ids=["api.refund"],
    ),
    # ---------- 用户与会员 ----------
    "user_info": KnowledgeIntent(
        id="user_info",
        description="用户资料咨询，例如昵称、手机号、常用出行人",
        provider_ids=["api.user"],
    ),
    "member_info": KnowledgeIntent(
        id="member_info",
        description="会员信息咨询，例如会员等级、积分余额、成长值",
        provider_ids=["api.user"],
    ),
    # ---------- 规则与政策 ----------
    "refund_policy": KnowledgeIntent(
        id="refund_policy",
        description="退款政策咨询，例如哪些情况可以退、退款到账时间",
        provider_ids=["faq.default"],
    ),
    "change_policy": KnowledgeIntent(
        id="change_policy",
        description="改期改签政策咨询，例如酒店、门票、车票能否改期",
        provider_ids=["faq.default"],
    ),
    "booking_rule": KnowledgeIntent(
        id="booking_rule",
        description="预订规则咨询，例如下单、支付时限、入住要求",
        provider_ids=["faq.default"],
    ),
    "travel_notice": KnowledgeIntent(
        id="travel_notice",
        description="出行须知咨询，例如证件、值机、入住与景区入园要求",
        provider_ids=["faq.default"],
    ),
    "general_travel": KnowledgeIntent(
        id="general_travel",
        description="旅游通用信息咨询，例如目的地玩法、季节与注意事项",
        provider_ids=["faq.default"],
    ),
}