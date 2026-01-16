from typing import Final

# Использовать ли эвристики при совпадении инициал преподавателей
# Если нет, то такие случаи будут пропускаться
USE_HEURISTICS_FOR_TEACHERS: Final[bool] = True

# Пропускать преподавателей, которых нет в списке преподавателей ТвГУ
SKIP_UNRECOGNIZED_TEACHERS: Final[bool] = False
