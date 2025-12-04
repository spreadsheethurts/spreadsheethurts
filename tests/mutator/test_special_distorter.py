from wizard.cell import Cell
from wizard.argumentation.mutator.special_distorter import SpecialDistorter


def test_special_distorter():

    class FakeDataset:
        def exists(self, s: str) -> bool:
            return False

    s = "11:11:"
    mutator = SpecialDistorter()
    for i in mutator.sample(s, 100, FakeDataset()):
        print(i)
