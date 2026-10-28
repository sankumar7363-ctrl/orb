from orb.gui.application import ORBGuiApplication
from orb.gui.main_window import ORBMainWindow


def main() -> int:
    application = ORBGuiApplication()

    window = ORBMainWindow(application)
    window.show()

    try:
        return application.run()
    finally:
        application.stop_orb()


if __name__ == "__main__":
    raise SystemExit(main())