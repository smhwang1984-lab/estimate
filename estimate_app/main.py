"""프로그램 시작 지점."""

import tkinter as tk

from .ui.dashboard import EstimateApp


def main():
    root = tk.Tk()
    EstimateApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
