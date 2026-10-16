from dataclasses import dataclass
from pathlib import Path
import re


RULES_FILE = Path(__file__).with_name("rules.txt")
GOAL = "Диагноз"


@dataclass(frozen=True)
class Rule:
    conditions: tuple[tuple[str, str], ...]
    conclusion: tuple[str, str]

    def __str__(self) -> str:
        left = " И ".join(f"{name}={value}" for name, value in self.conditions)
        name, value = self.conclusion
        return f"ЕСЛИ {left} ТО {name}={value}"


def parse_pair(text: str) -> tuple[str, str]:
    if text.count("=") != 1:
        raise ValueError(f"Некорректная пара Объект=Значение: {text}")
    name, value = (part.strip() for part in text.split("=", 1))
    if not name or not value:
        raise ValueError(f"Объект и значение не должны быть пустыми: {text}")
    return name, value


def parse_rule(line: str) -> Rule:
    match = re.fullmatch(r"\s*ЕСЛИ\s+(.+?)\s+ТО\s+(.+?)\s*", line)
    if not match:
        raise ValueError("Ожидается формат: ЕСЛИ ... ТО Объект=Значение")

    conditions = tuple(
        parse_pair(part)
        for part in re.split(r"\s+И\s+", match.group(1))
    )
    if not conditions:
        raise ValueError("У правила должно быть хотя бы одно условие")

    return Rule(conditions, parse_pair(match.group(2)))


def load_rules(path: Path = RULES_FILE) -> list[Rule]:
    rules = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        content = line.strip()
        if not content or content.startswith("#"):
            continue
        try:
            rules.append(parse_rule(content))
        except ValueError as error:
            raise ValueError(
                f"Ошибка в файле правил, строка {line_number}: {error}"
            ) from error
    return rules


def save_rules(rules: list[Rule], path: Path = RULES_FILE) -> None:
    path.write_text(
        "\n".join(str(rule) for rule in rules) + "\n",
        encoding="utf-8",
    )


def print_rules(rules: list[Rule]) -> None:
    print("\n=== БАЗА ПРАВИЛ ===")
    if not rules:
        print("Правила отсутствуют.")
        return
    for i, rule in enumerate(rules, 1):
        print(f"{i}. {rule}")


def print_facts(facts: dict[str, str]) -> None:
    print("\n=== РАБОЧАЯ БАЗА ДАННЫХ ===")
    if not facts:
        print("Факты отсутствуют.")
        return
    for name, value in facts.items():
        print(f"{name} = {value}")


# True — доказано, False — недостижимо по базе, None — недостаточно данных.
def backward_chain(rules, facts, goal, ask_fact=None):
    memory = dict(facts)
    trace = []
    unanswered = set()
    derived_names = {rule.conclusion[0] for rule in rules}

    def prove(target, visiting, depth):
        name, value = target
        label = f"{name}={value}"
        def log(message):
            trace.append("  " * depth + message)
        log(f"Цель: {label}")
        if name in memory:
            success = memory[name] == value
            log(f"В памяти {name}={memory[name]}: " +
                ("подтверждено" if success else "противоречие"))
            return success
        if target in visiting:
            log("Цикл: эта цель уже проверяется в текущей ветви.")
            return False
        candidates = [(i, r) for i, r in enumerate(rules, 1)
                      if r.conclusion == target]
        if not candidates:
            if name in derived_names:
                log("Нет правила для получения этого значения.")
                return False
            if ask_fact is not None and name not in unanswered:
                supplied = ask_fact(name, value)
                if supplied is not None and str(supplied).strip():
                    memory[name] = str(supplied).strip()
                    log(f"Получен факт {name}={memory[name]}")
                    return memory[name] == value
                unanswered.add(name)
            log("Значение исходного факта неизвестно.")
            return None
        unknown = False
        for index, rule in candidates:
            log(f"Проверка правила {index}: {rule}")
            outcomes = []
            for condition in rule.conditions:
                outcome = prove(condition, visiting | {target}, depth + 1)
                outcomes.append(outcome)
                if outcome is False:
                    break
            if False in outcomes:
                log(f"Правило {index} отклонено.")
            elif None in outcomes:
                unknown = True
                log(f"Правилу {index} не хватает данных.")
            else:
                memory[name] = value
                log(f"Правило {index} доказало {label}")
                return True
        return None if unknown else False

    result = prove(goal, frozenset(), 0)
    return result, memory, trace


def ask_fact(name, expected_value):
    return input(f"Значение «{name}» (Enter — неизвестно): ").strip()


def read_initial_facts():
    facts = {}
    print("Введите начальные факты Объект=Значение, каждый с новой строки.")
    print("Пустая строка завершает ввод. Регистр значений учитывается.")
    while True:
        line = input("> ").strip()
        if not line:
            return facts
        try:
            name, value = parse_pair(line)
            facts[name] = value
        except ValueError as error:
            print(f"Ошибка: {error}")


def run_expert_system():
    rules = load_rules()
    facts = read_initial_facts()
    print_facts(facts)
    goals = list(dict.fromkeys(r.conclusion for r in rules
                               if r.conclusion[0] == GOAL))
    print("\nДоступные диагнозы:")
    for index, (name, value) in enumerate(goals, 1):
        print(f"{index}. {name}={value}")
    while True:
        raw = input("Цель: номер диагноза или Объект=Значение: ").strip()
        try:
            if raw.isdecimal():
                index = int(raw)
                if not 1 <= index <= len(goals):
                    raise ValueError("Неверный номер цели")
                goal = goals[index - 1]
            else:
                goal = parse_pair(raw)
            break
        except ValueError as error:
            print(f"Ошибка: {error}")
    interactive = input("Запрашивать недостающие факты? (да/нет): ").strip() == "да"
    result, memory, trace = backward_chain(
        rules, facts, goal, ask_fact if interactive else None)
    print("\n=== ХОД ОБРАТНОГО ВЫВОДА ===")
    print("\n".join(trace))
    print_facts(memory)
    print("\n=== РЕЗУЛЬТАТ ===")
    if result is True:
        print("Целевая ситуация доказана.")
    elif result is False:
        print("Целевая ситуация недостижима при заданных фактах и правилах.")
    else:
        print("Недостаточно данных для доказательства или опровержения цели.")


def add_rule(rules: list[Rule]) -> None:
    print("\nВведите правило, заменив пример конкретными признаками:")
    print("ЕСЛИ Компьютер_включается=да И Корпус_перегревается=да "
          "ТО Диагноз=вероятный_перегрев_компьютера")
    line = input("> ").strip()

    try:
        rule = parse_rule(line)
    except ValueError as error:
        print(f"Ошибка: {error}")
        return

    pairs = (*rule.conditions, rule.conclusion)
    if any(
        name.casefold() == "объект" and value.casefold() == "значение"
        for name, value in pairs
    ):
        print(
            "Ошибка: введён шаблон. Замените «Объект» и «Значение» "
            "конкретными признаками и значениями. Правило не сохранено."
        )
        return

    rules.append(rule)
    save_rules(rules)
    if rule.conclusion[0] == GOAL:
        print(
            "Правило добавлено. Если его условия выполнятся, оно сможет "
            "вывести указанный диагноз. Неизвестные условия система "
            "сможет спросить при следующей консультации."
        )
    else:
        print(
            "Правило добавлено. Оно повлияет на диагноз, если его "
            "заключение используется в другой цепочке, ведущей к «Диагноз»."
        )


def edit_rule(rules: list[Rule]) -> None:
    print_rules(rules)
    if not rules:
        return

    try:
        index = int(input("Номер правила для изменения: ")) - 1
        if not 0 <= index < len(rules):
            raise ValueError
    except ValueError:
        print("Некорректный номер.")
        return

    print(f"Текущее правило: {rules[index]}")
    line = input("Новое правило: ").strip()

    try:
        rules[index] = parse_rule(line)
    except ValueError as error:
        print(f"Ошибка: {error}")
        return

    save_rules(rules)
    print("Правило изменено.")


def delete_rule(rules: list[Rule]) -> None:
    print_rules(rules)
    if not rules:
        return

    try:
        index = int(input("Номер правила для удаления: ")) - 1
        if not 0 <= index < len(rules):
            raise ValueError
    except ValueError:
        print("Некорректный номер.")
        return

    deleted = rules.pop(index)
    save_rules(rules)
    print(f"Удалено правило: {deleted}")


def rules_menu() -> None:
    try:
        rules = load_rules()
    except ValueError as error:
        print(f"Ошибка загрузки базы правил: {error}")
        return

    while True:
        print("\n=== РЕДАКТИРОВАНИЕ БАЗЫ ПРАВИЛ ===")
        print("1. Показать правила")
        print("2. Добавить правило")
        print("3. Изменить правило")
        print("4. Удалить правило")
        print("0. Назад")

        choice = input("Выберите действие: ").strip()

        if choice == "1":
            print_rules(rules)
        elif choice == "2":
            add_rule(rules)
        elif choice == "3":
            edit_rule(rules)
        elif choice == "4":
            delete_rule(rules)
        elif choice == "0":
            break
        else:
            print("Неизвестная команда.")


def main():
    while True:
        print("\nЛАБОРАТОРНАЯ №2: ОБРАТНАЯ ЦЕПОЧКА РАССУЖДЕНИЙ")
        print("1. Проверить целевую ситуацию")
        print("2. Показать базу правил")
        print("3. Редактировать базу правил")
        print("0. Выход")
        try:
            choice = input("Выберите действие: ").strip()
            if choice == "1":
                run_expert_system()
            elif choice == "2":
                print_rules(load_rules())
            elif choice == "3":
                rules_menu()
            elif choice == "0":
                print("Работа завершена.")
                return
            else:
                print("Неизвестная команда.")
        except (ValueError, OSError) as error:
            print(f"Ошибка: {error}")
        except (EOFError, KeyboardInterrupt):
            print("\nРабота завершена.")
            return


if __name__ == "__main__":
    main()
