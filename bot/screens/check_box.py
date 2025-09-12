class CheckBox:
    def __init__(self, selected:bool = False, text: str = ""):
        self._selected = selected
        self.text = text

    def check(self):
        self._selected = True