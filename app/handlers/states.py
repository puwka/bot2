from aiogram.fsm.state import State, StatesGroup


class AdminCreateTopic(StatesGroup):
    waiting_name = State()


class AdminCreateUser(StatesGroup):
    waiting_telegram_id = State()
    waiting_role = State()


class AdminAssignRole(StatesGroup):
    waiting_user = State()
    waiting_role = State()


class AdminAssignCategory(StatesGroup):
    waiting_user = State()
    waiting_topic = State()


class AdminStatsUser(StatesGroup):
    waiting_user = State()


class AdminReassign(StatesGroup):
    waiting_dist_id = State()
    waiting_user = State()


class UploaderAddVideo(StatesGroup):
    waiting_topic = State()
    waiting_video = State()  # видеофайл или ссылка
    waiting_description = State()  # только для загрузки по ссылке


class DistSubmitResult(StatesGroup):
    waiting_url = State()
