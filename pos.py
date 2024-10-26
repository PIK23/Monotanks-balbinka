from dataclasses import dataclass

@dataclass(unsafe_hash=True, frozen=False)
class Pos():
    x: int
    y: int 
    def __getitem__(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y