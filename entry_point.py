import multiprocessing
import sys

if __name__ == '__main__':
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn", force=True)

    if '--run-aura' in sys.argv:
        import main
        main.main()
        sys.exit(0)

    # Launch the PyQt6 dashboard as default
    import gui
    gui.main()
