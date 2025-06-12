from unittest import TestCase
from unittest.mock import MagicMock, patch
from combat.combat_utils import calculate_initiative

class Dummy:
    def __init__(self, init=0, level=1, bonus=0):
        self.traits = MagicMock()
        self.traits.get.return_value = MagicMock(value=init)
        self.db = type("DB", (), {"level": level})()
        self.equipment = {"slot": MagicMock()}
        self.equipment["slot"].attributes = MagicMock()
        self.equipment["slot"].attributes.get.return_value = bonus

class TestInitiativeCalculation(TestCase):
    def test_calculate_initiative(self):
        d = Dummy(init=5, level=8, bonus=2)
        with patch("random.randint", return_value=4):
            result = calculate_initiative(d)
        self.assertEqual(result, 5 + 2 + (8 // 4) + 4)
