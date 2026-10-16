import unittest
from main import backward_chain, load_rules, parse_rule


class BackwardChainTests(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules()
        self.goal = ('Диагноз', 'проверить_видеокарту_кабель_и_монитор')
        self.facts = dict(Компьютер_включается='да', Экран_черный='да',
                          Звук_загрузки='да', Изображение_на_мониторе='нет')

    def test_three_rule_chain_and_input_unchanged(self):
        result, memory, trace = backward_chain(self.rules, self.facts, self.goal)
        self.assertIs(result, True)
        self.assertEqual(memory['Диагноз'], self.goal[1])
        self.assertNotIn('Диагноз', self.facts)
        for number in (8, 5, 1):
            self.assertTrue(any(f'Правило {number} доказало' in s for s in trace))

    def test_contradiction(self):
        self.facts['Звук_загрузки'] = 'нет'
        self.assertIs(backward_chain(self.rules, self.facts, self.goal)[0], False)

    def test_missing_data_is_not_refutation(self):
        self.assertIs(backward_chain(self.rules, {}, self.goal)[0], None)

    def test_questions_only_for_relevant_inputs(self):
        asked = []
        def ask(name, expected):
            asked.append(name)
            return self.facts[name]
        self.assertIs(backward_chain(self.rules, {}, self.goal, ask)[0], True)
        self.assertEqual(set(asked), set(self.facts))

    def test_cycle_with_alternative(self):
        rules = [parse_rule(s) for s in [
            'ЕСЛИ Б=да ТО А=да', 'ЕСЛИ А=да ТО Б=да',
            'ЕСЛИ В=да ТО А=да']]
        self.assertIs(backward_chain(rules, {'В': 'да'}, ('А', 'да'))[0], True)
        self.assertIs(backward_chain(rules[:2], {}, ('А', 'да'))[0], False)

    def test_alternative_after_unknown_branch(self):
        rules = [parse_rule(s) for s in [
            'ЕСЛИ А=да ТО Цель=да', 'ЕСЛИ Б=да ТО Цель=да']]
        self.assertIs(backward_chain(rules, {'Б': 'да'}, ('Цель', 'да'))[0], True)

    def test_power_chain(self):
        facts = dict(Компьютер_включается='нет', Индикаторы_горят='нет',
                     Вентиляторы_вращаются='нет', Розетка_работает='да')
        goal = ('Диагноз', 'проверить_блок_питания_и_кабель')
        self.assertIs(backward_chain(self.rules, facts, goal)[0], True)


if __name__ == '__main__':
    unittest.main()
