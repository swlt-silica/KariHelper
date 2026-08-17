"""借物表生成器 - 入口。运行: python app.py"""
from main_window import MainWindow


def main():
    import config
    config.ensure_dirs()
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
