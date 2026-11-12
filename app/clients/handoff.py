from app.service.handoff_service import HandoffService

# 应用级共享服务，Action 与 Web 接口共用
_handoff_service: HandoffService | None = None


def get_handoff_service() -> HandoffService:
    global _handoff_service
    if _handoff_service is None:
        _handoff_service = HandoffService()
    return _handoff_service


def set_handoff_service(
    service: HandoffService | None,
) -> None:
    """替换全局服务，主要用于测试。"""
    global _handoff_service
    _handoff_service = service