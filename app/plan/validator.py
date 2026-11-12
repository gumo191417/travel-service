from app.domain.command import (
    CancelTaskCommand,
    ResumeTaskCommand,
    SetSlotsCommand,
    StartFlowCommand,
)
from app.domain.flow_catalog import FlowCatalog
from app.domain.plan import (
    ClarifyReason,
    KnowledgeTurnPlan,
    TaskTurnPlan,
    TurnPlan,
    TurnPlanValidationResult,
)
from app.domain.state import DialogueState
from app.knowledge.intents import KnowledgeIntent


class TurnPlanValidator:
    """用确定性规则校验 TurnPlan 能否在当前状态下执行，只返回结果。"""

    def validate(
        self,
        turn_plan: TurnPlan,
        state: DialogueState,
        flow_catalog: FlowCatalog,
        knowledge_intents: dict[str, KnowledgeIntent],
    ) -> TurnPlanValidationResult:
        # 1. 收集计划命中的处理方向
        active_tracks = self._active_tracks(turn_plan)

        # 2. 没有方向或多于一个方向，都需要澄清
        if not active_tracks:
            return self._reject(ClarifyReason.MISSING_TRACK)
        if len(active_tracks) > 1:
            return self._reject(ClarifyReason.MULTIPLE_TRACKS)

        # 3. 按唯一方向分派校验
        track = active_tracks[0]
        if track == "task":
            return self._validate_task(
                turn_plan.task,
                state,
                flow_catalog,
            )
        if track == "knowledge":
            return self._validate_knowledge(
                turn_plan.knowledge,
                state,
                knowledge_intents,
            )

        # 4. 闲聊方向没有额外内容，直接通过
        return TurnPlanValidationResult(valid=True)

    @staticmethod
    def _active_tracks(turn_plan: TurnPlan) -> list[str]:
        # 非 None 的方向即为命中
        active_tracks: list[str] = []
        if turn_plan.task is not None:
            active_tracks.append("task")
        if turn_plan.knowledge is not None:
            active_tracks.append("knowledge")
        if turn_plan.chitchat is not None:
            active_tracks.append("chitchat")
        return active_tracks

    @staticmethod
    def _reject(reason: ClarifyReason) -> TurnPlanValidationResult:
        # 统一构造失败结果
        return TurnPlanValidationResult(
            valid=False,
            reason=reason,
        )

    def _validate_task(
        self,
        task: TaskTurnPlan,
        state: DialogueState,
        flow_catalog: FlowCatalog,
    ) -> TurnPlanValidationResult:
        # 1. 任务计划必须至少包含一个 Command
        if not task.commands:
            return self._reject(
                ClarifyReason.MISSING_TASK_COMMANDS
            )

        # 2. 按执行顺序模拟任务状态，逐条校验
        #    （start_flow 之后 set_slots 才合法，不能只看初始状态）
        active_task_id = (
            state.task_state.active_task.task_id
            if state.task_state.active_task is not None
            else None
        )
        paused_task_ids = {
            paused.task_id
            for paused in state.task_state.paused
        }

        for command in task.commands:

            if isinstance(command, StartFlowCommand):
                # 流程 ID 必须存在
                if flow_catalog.get_flow(command.flow) is None:
                    return self._reject(
                        ClarifyReason.INVALID_TASK_COMMAND
                    )
                # 新任务成为活动任务，原活动任务进入暂停
                if active_task_id is not None:
                    paused_task_ids.add(active_task_id)
                active_task_id = f"new:{command.flow}"

            elif isinstance(command, SetSlotsCommand):
                # Slot 必须是非空字典，且当前确实存在活动任务
                if not isinstance(command.slots, dict):
                    return self._reject(
                        ClarifyReason.INVALID_TASK_COMMAND
                    )
                if not command.slots:
                    return self._reject(
                        ClarifyReason.INVALID_TASK_COMMAND
                    )
                if active_task_id is None:
                    return self._reject(
                        ClarifyReason.INVALID_TASK_COMMAND
                    )
                for slot_name in command.slots:
                    if slot_name not in flow_catalog.slots:
                        return self._reject(
                            ClarifyReason.INVALID_TASK_COMMAND
                        )

            elif isinstance(command, ResumeTaskCommand):
                # 只能恢复暂停中的任务
                if command.task_id not in paused_task_ids:
                    return self._reject(
                        ClarifyReason.INVALID_TASK_COMMAND
                    )
                paused_task_ids.remove(command.task_id)
                if active_task_id is not None:
                    paused_task_ids.add(active_task_id)
                active_task_id = command.task_id

            elif isinstance(command, CancelTaskCommand):
                # 只能取消活动或暂停中的任务
                if command.task_id == active_task_id:
                    active_task_id = None
                elif command.task_id in paused_task_ids:
                    paused_task_ids.remove(command.task_id)
                else:
                    return self._reject(
                        ClarifyReason.INVALID_TASK_COMMAND
                    )

            else:
                # 未知命令（Command.from_dict 的占位对象）
                return self._reject(
                    ClarifyReason.INVALID_TASK_COMMAND
                )

        # 3. 全部 Command 通过
        return TurnPlanValidationResult(valid=True)

    def _validate_knowledge(
        self,
        knowledge_turn_plan: KnowledgeTurnPlan,
        state: DialogueState,
        knowledge_intents: dict[str, KnowledgeIntent],
    ) -> TurnPlanValidationResult:
        # 1. 知识计划必须至少包含一个 Intent
        if not knowledge_turn_plan.intents:
            return self._reject(
                ClarifyReason.MISSING_KNOWLEDGE_INTENT
            )

        # 2. 逐个 Intent 检查支持性与所需对象
        for intent_id in knowledge_turn_plan.intents:
            # Intent 必须属于系统支持的知识意图
            if intent_id not in knowledge_intents:
                return self._reject(
                    ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT
                )

            knowledge_intent = knowledge_intents[intent_id]
            required_object = knowledge_intent.requires_object
            focused_object = state.shared_state.focused_object

            # 要求对象时，聚焦对象必须存在且类型一致
            if required_object and (
                focused_object is None
                or focused_object.type != required_object
            ):
                return self._reject(
                    ClarifyReason.MISSING_FOCUSED_OBJECT
                )

        # 3. 全部 Intent 通过
        return TurnPlanValidationResult(valid=True)